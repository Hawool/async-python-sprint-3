import asyncio
import logging
import sys

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.addHandler(logging.StreamHandler(stream=sys.stdout))


class Client:
    def __init__(self, username, server_host='127.0.0.1', server_port=8000):
        self.server_host = server_host
        self.server_port = server_port
        self.reader = None
        self.writer = None
        self.username = username

    async def start(self) -> None:
        logger.info(f'Start Client {self.username}')
        self.reader, self.writer = await asyncio.open_connection(self.server_host, self.server_port)
        print(f"Connected to {self.server_host}:{self.server_port}")
        self.writer.write(f"{self.username}\n".encode())
        await asyncio.gather(self.listen(), self.send())

    async def listen(self) -> None:
        while True:
            message = await self.reader.readline()
            if not message:
                break
            message = message.decode().strip()

    async def send(self) -> None:
        for i in range(5):
            message = f'message_{i}'
            await asyncio.sleep(1)
            self.writer.write(f"{message}\n".encode())
            await self.writer.drain()


async def main() -> None:
    client = Client('Bob')
    await client.start()


if __name__ == '__main__':
    asyncio.run(main())
