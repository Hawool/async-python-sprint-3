import asyncio
import logging
import pickle
import sys

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.addHandler(logging.StreamHandler(stream=sys.stdout))


class Chat:
    messages_store = []
    clients = []


class Server:
    def __init__(self, host='127.0.0.1', port=8000):
        self.clients = {}
        self.server = None
        self.host = host
        self.port = port
        self.messages_store = []
        self.chats = []
        self.history_file = 'history_server.txt'

        self.restore_server_history()

    async def listen(self):
        self.server = await asyncio.start_server(self.handle_client, self.host, self.port)
        print(f'Listening on {self.host}:{self.port}')
        await self.server.serve_forever()

    async def handle_client(self, client_reader, client_writer):
        username = await client_reader.readline()
        username = username.decode().strip()

        if self.check_if_user_exist(username):
            await self.send_last_messages_to_client(client_writer)
        else:
            message = f'New client {username}'
            print(message)
            self.messages_store.append(message)
            self.clients[username] = client_writer
            await self.broadcast(message, username)

        try:
            while True:
                message = await client_reader.readline()
                if not message:
                    break

                if message.decode().startswith('quit'):
                    break

                if message.decode().startswith('POST /connect'):
                    # parse the GET request
                    request_path = message.split()[1]
                    print(f'Received POST request for path: {request_path}')
                    # send a response to the client
                    client_writer.write(b'HTTP/1.1 200 OK\n\n')
                    client_writer.write(b'Hello, World!')
                    await client_writer.drain()
                    break

                if message.decode().startswith('GET /status'):
                    # parse the GET request
                    request_path = message.split()[1]
                    print(f'Received GET request for path: {request_path}')
                    # send a response to the client
                    client_writer.write(b'HTTP/1.1 200 OK\n\n')
                    client_writer.write(b'Hello, World!')
                    await client_writer.drain()
                    break

                if message.decode().startswith('POST /send'):
                    # parse the GET request
                    request_path = message.split()[1]
                    print(f'Received POST request for path: {request_path}')
                    # send a response to the client
                    client_writer.write(b'HTTP/1.1 200 OK\n\n')
                    client_writer.write(b'Hello, World!')
                    await client_writer.drain()
                    break

                message = message.decode().strip()
                message = f'{username}: {message}'
                self.messages_store.append(message)
                print(message)
                await self.broadcast(message, username)
        except Exception as e:
            print(e)
        finally:
            client_writer.close()

    async def broadcast(self, message, username):
        for user, client in self.clients.items():
            if user != username:
                client.write(f'{message}\n'.encode())
                await client.drain()

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
            logger.info(f'File for restore message was not found, {error=}')


async def main():
    server = Server()
    await server.listen()


if __name__ == '__main__':
    asyncio.run(main())
