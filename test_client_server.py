import pytest

from client import Client
from server import Server


@pytest.fixture
def server_client():
    server = Server()
    client = Client('Bob')
    return server, client


@pytest.mark.asyncio
async def test_server_client(server_client):
    server, client = server_client

    # на этом моменте сервер зависает на бесконечном цикле и клиент не запускается, не знаю как тут сделать правильно
    await server.listen()
    await client.start()
    client.writer.write(b"Hello, world!\n")
    await client.writer.drain()
    message = server.messages_store[0]
    message = message.strip()
    assert message == "Hello, world!"
