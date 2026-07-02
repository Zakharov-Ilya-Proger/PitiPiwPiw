from os import  getenv

from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):

    db_url: str = getenv('DB_URL')
    admin_pwd: str = getenv('ADMIN_PWD') or 'admin'

    class Config:
        env_file = '.env'
        env_file_encoding = 'utf-8'

settings = Settings()

__all__=[
    'settings'
]