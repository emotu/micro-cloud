"""
config.py

The base settings file for the project. This file will be imported by any modules that require settings functionality.
All variables and paths are loaded up from the environmental variables setup by in the .env file in use.
"""
import os
from functools import lru_cache
from typing import Optional

from pydantic import PositiveInt
from pydantic_settings import BaseSettings, SettingsConfigDict

# import the necessary
# .env file based on what environment you are in
# The base folder will be the env folder at the root of the project
env = os.getenv("ENV", "dev")  # get environment


class Settings(BaseSettings):
    """ Application settings based on pydantic model """

    API_NAME: str = "Personal Cloud API"
    API_VERSION: str = "1.0.0"
    API_PREFIX: Optional[str] = None
    ENV: str = "staging"
    DB_NAME: str
    DB_HOSTNAME: str
    MONGO_USERNAME: str | None = None
    MONGO_URI_PARAMS: str | None = None
    MONGO_PASSWORD: str | None = None
    DB_PORT: PositiveInt
    RESET_EXPIRES_IN_HOURS: int = 24
    JWT_EXPIRES_IN_HOURS: int = 48
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str
    JWT_ISSUER_CLAIM: str

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


# Using lru_cache to prevent settings from getting reinitialized on every call.
@lru_cache
def get_settings():
    _settings = Settings()
    return _settings


# initialize settings so it is available from config
settings = get_settings()
