import asyncio
import json
import logging
import pickle
import sys

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.addHandler(logging.StreamHandler(stream=sys.stdout))


class Chat:
    names: list[str] = []

    def __init__(self, name, messages_store: list[str], clients: set[str]):
        self.name = name
        self.messages_store = messages_store if messages_store else []
        self.clients = clients if clients else set()

        self.add_name()

    def add_name(self):
        self.names.append(self.name)


class Server:
    def __init__(self, host='127.0.0.1', port=8000):
        self.clients = {}
        self.server = None
        self.host = host
        self.port = port
        self.messages_store = []
        self.main_chat = Chat(name='main', messages_store=[], clients=set())
        self.chats = {'main': self.main_chat}
        self.history_file = 'history_server.txt'

        self.restore_server_history()

    async def listen(self):
        self.server = await asyncio.start_server(self.handle_client, self.host, self.port)
        print(f'Listening on http://{self.host}:{self.port}')
        await self.server.serve_forever()

    async def handle_client(self, client_reader, client_writer):
        username = await client_reader.readline()
        username = username.decode().strip()
        self.clients[username] = client_writer
        self.main_chat.clients.add(username)

        if self.check_if_user_exist(username):
            await self.send_last_messages_to_client(client_writer)
        else:
            message = f'New client {username}'
            print(message)
            self.messages_store.append(message)
            await self.broadcast(message, username)

        try:
            while True:
                message = await client_reader.readline()
                if not message:
                    break

                if message.decode().startswith('quit'):
                    break

                if message.decode().startswith('GET /chat'):
                    """Метод получения списка чатов"""
                    await self.get_chats(message, client_writer)
                    continue

                if message.decode().startswith('POST /chat'):
                    """Метод создания чата или переход в существующий"""
                    await self.create_chat(message, username, client_writer)
                    continue

                if message.decode().startswith('POST /send'):
                    """Метод отправки сообщения определенному клиенту"""
                    await self.send_to_one_client(message, username)
                    continue

                message = message.decode().strip()
                message = f'{username}: {message}'
                self.messages_store.append(message)
                print(message)
                await self.broadcast(message, username)
        except Exception as e:
            print(e)
        finally:
            self.clients[username] = None
            client_writer.close()

    async def broadcast(self, message, write_username):
        """Отправляет сообщения всем клиентам в своем чате кроме себя"""
        for user, client_writer in self.clients.items():
            for chat_name, chat in self.chats.items():
                if user in chat.clients and write_username in chat.clients and user != write_username:
                    client_writer.write(f'{message}\n'.encode())
                    await client_writer.drain()

    def check_if_user_exist(self, username) -> bool:
        return True if username in self.clients.keys() else False

    async def send_last_messages_to_client(self, client_writer):
        for message in self.messages_store[-20:]:
            client_writer.write(f'{message}\n'.encode())
            await client_writer.drain()

    def restore_server_history(self):
        try:
            with open(self.history_file, 'rb') as file:
                self.messages_store = pickle.load(file)
        except FileNotFoundError as error:
            logger.debug(f'File for restore message was not found, {error=}')

    async def create_chat(self, message, username, client_writer):
        """Отправляет клиента в чат, создает его если нет, берет существующий если есть"""
        request_path = message.decode().split()[1]
        logger.info(f'Received POST request for path: {request_path}')
        chat_name = message.decode().split()[2]
        if chat_name in Chat.names:
            new_chat = next(filter(lambda x: x.name == chat_name, self.chats.values()), None)
        else:
            new_chat = Chat(name=chat_name, messages_store=[], clients=set())
            self.chats[new_chat.name] = new_chat
        new_chat.clients.add(username)
        # удаляем клиента из главного чата
        self.delete_client_from_his_chat(username)
        # self.main_chat.clients.remove(username)
        # добавляем в новый
        new_chat.clients.add(username)
        logger.info(f'New chat {new_chat.name} was created')
        message = f'You moved to {new_chat.name} chat\n'
        client_writer.write(message.encode())
        await client_writer.drain()

    async def get_chats(self, message, client_writer):
        request_path = message.decode().split()[1]
        logger.info(f'Received GET request for path: {request_path}')
        chat_names = [chat.name for chat in self.chats.values()]
        message_json = json.dumps(chat_names)
        client_writer.write(message_json.encode())
        await client_writer.drain()

    async def send_to_one_client(self, message, username):
        request_path = message.decode().split()[1]
        logger.info(f'Received POST request for path: {request_path}')
        client_name = message.decode().split()[2]
        client_message = message.decode().split()[3]
        for user, client_writer in self.clients.items():
            if client_name == user:
                message = f'{username}: {client_message}\n'
                client_writer.write(message.encode())
                await client_writer.drain()

    def delete_client_from_his_chat(self, username):
        """Удаляет клиента из чата в котором он сейчас находится"""
        for _, chat in self.chats.items():
            if username in chat.clients:
                chat.clients.remove(username)


async def main():
    server = Server()
    await server.listen()


if __name__ == '__main__':
    asyncio.run(main())
