import asyncio
import json
import pickle
from asyncio import StreamReader, StreamWriter, IncompleteReadError

from config import ServerConfig
from log_settings import logger


class Chat:
    names: list[str] = []

    def __init__(self, name: str, messages_store: list[str], clients: set):
        self.name = name
        self.messages_store = messages_store if messages_store else []
        self.clients = clients if clients else set()

        self.add_name()

    def add_name(self):
        self.names.append(self.name)


class Server:
    def __init__(self):
        self.clients = {}
        self.server = None
        self.config = ServerConfig()
        self.messages_store = []
        self.main_chat = Chat(name='main', messages_store=[], clients=set())
        self.chats = {'main': self.main_chat}
        self.history_file = 'history_server.txt'

        self.restore_server_history()

    async def listen(self):
        self.server = await asyncio.start_server(self.handle_client, self.config.HOST, self.config.PORT)
        print(f'Listening on http://{self.config.HOST}:{self.config.PORT}')
        await self.server.serve_forever()

    async def stop(self):
        self.server.close()
        await self.server.wait_closed()
        # write the chat history to a file
        with open(self.history_file, 'wb') as f:
            pickle.dump(self.chats, f)
        logger.info('Server stopped')

    async def handle_client(self, client_reader: StreamReader, client_writer: StreamWriter) -> None:
        username_bytes: bytes = await client_reader.readline()
        username: str = username_bytes.decode().strip()
        self.clients[username] = client_writer
        self.main_chat.clients.add(username)

        if self.check_if_user_exist(username):
            await self.send_last_messages_to_client(client_writer)
        else:
            new_client_message = f'New client {username}'
            print(new_client_message)
            self.messages_store.append(new_client_message)
            await self.broadcast(new_client_message, username)

        try:
            while True:
                message_bytes: bytes = await client_reader.readline()
                if not message_bytes:
                    break

                if message_bytes.decode().startswith('quit'):
                    break

                if message_bytes.decode().startswith('/chats'):
                    """Метод получения списка чатов"""
                    await self.get_chats(message_bytes, client_writer)
                    continue

                if message_bytes.decode().startswith('/get_chat'):
                    """Метод создания чата или переход в существующий"""
                    await self.create_chat(message_bytes, username, client_writer)
                    continue

                if message_bytes.decode().startswith('/send'):
                    """Метод отправки сообщения определенному клиенту"""
                    await self.send_to_one_client(message_bytes, username)
                    continue

                message: str = message_bytes.decode().strip()
                message = f'{username}: {message}'
                self.messages_store.append(message)
                print(message)
                await self.broadcast(message, username)
        except IncompleteReadError as error:
            logger.error(f'Server catch IncompleteReadError: {error}')
        finally:
            self.clients[username] = None  # type: ignore
            client_writer.close()

    async def broadcast(self, message: str, write_username: str) -> None:
        """Отправляет сообщения всем клиентам в своем чате кроме себя"""
        for user, client_writer in self.clients.items():
            for chat_name, chat in self.chats.items():
                if user in chat.clients and write_username in chat.clients and user != write_username:
                    client_writer.write(f'{message}\n'.encode())
                    await client_writer.drain()

    def check_if_user_exist(self, username: str) -> bool:
        return True if username in self.clients.keys() else False

    async def send_last_messages_to_client(self, client_writer: StreamWriter) -> None:
        for message in self.messages_store[-20:]:
            client_writer.write(f'{message}\n'.encode())
            await client_writer.drain()

    def restore_server_history(self) -> None:
        try:
            with open(self.history_file, 'rb') as file:
                self.chats = pickle.load(file)
        except FileNotFoundError as error:
            logger.debug(f'File for restore message was not found, {error=}')

    async def create_chat(self, message: bytes, username: str, client_writer: StreamWriter) -> None:
        """Отправляет клиента в чат, создает его если нет, берет существующий если есть"""
        request_path = message.decode().split()[1]
        logger.debug(f'Received request for path: {request_path}')
        chat_name: str = message.decode().split()[1]
        if chat_name in Chat.names:
            new_chat = next(filter(lambda x: x.name == chat_name, self.chats.values()), None)
        else:
            new_chat = Chat(name=chat_name, messages_store=[], clients=set())
            self.chats[new_chat.name] = new_chat
        if new_chat is not None:
            # удаляем клиента из главного чата
            self.delete_client_from_his_chat(username)
            # self.main_chat.clients.remove(username)
            # добавляем в новый
            new_chat.clients.add(username)
            logger.info(f'New chat {new_chat.name} was created')
            message_moved = f'You moved to {new_chat.name} chat\n'
            client_writer.write(message_moved.encode())
            await client_writer.drain()

    async def get_chats(self, message: bytes, client_writer: StreamWriter) -> None:
        request_path = message.decode().split()[0]
        logger.debug(f'Received request for path: {request_path}')
        chat_names = [chat.name for chat in self.chats.values()]
        message_json = json.dumps(chat_names)
        client_writer.write(message_json.encode())
        await client_writer.drain()

    async def send_to_one_client(self, message: bytes, username: str) -> None:
        request_path = message.decode().split()[1]
        logger.debug(f'Received request for path: {request_path}')
        client_name = message.decode().split()[1]
        client_message = message.decode().split()[2]
        for user, client_writer in self.clients.items():
            if client_name == user:
                prepared_message = f'{username}: {client_message}\n'
                client_writer.write(prepared_message.encode())
                await client_writer.drain()

    def delete_client_from_his_chat(self, username: str) -> None:
        """Удаляет клиента из чата в котором он сейчас находится"""
        for _, chat in self.chats.items():
            if username in chat.clients:
                chat.clients.remove(username)


async def main() -> None:
    server = Server()
    await server.listen()


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info('Server is disabled')
