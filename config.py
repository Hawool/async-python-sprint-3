from pydantic import BaseSettings


class ServerConfig(BaseSettings):
    HOST: str = '127.0.0.1'
    PORT: int = 8000

    class Config:
        env_file = '.env'
