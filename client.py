import asyncio

from config import ServerConfig
from log_settings import logger


class Client:
    def __init__(self, username):
        self.config = ServerConfig()
        self.reader = None
        self.writer = None
        self.username = username

    async def start(self) -> None:
        logger.info(f'Start Client {self.username}')
        self.reader, self.writer = await asyncio.open_connection(self.config.HOST, self.config.PORT)
        print(f"Connected to {self.config.HOST}:{self.config.PORT}")
        self.writer.write(f"{self.username}\n".encode())
        await asyncio.gather(self.listen(), self.send())

    async def listen(self) -> None:
        while True:
            message = await self.reader.readline()
            if not message:
                break
            message = message.decode().strip()
            print(f"{message}")

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
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info('Client is disabled')
