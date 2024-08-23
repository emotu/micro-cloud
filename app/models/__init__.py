import sys

from inspect import getmembers, isclass
from typing import TypeVar, Type

from beanie import init_beanie
from motor.motor_asyncio import AsyncIOMotorClient

from .shared import *
from .auth import *
from .user import *
from .shared import *

# from .shipment import *


DocType = TypeVar("DocType", bound=Document)


class Database:
    db = None

    @classmethod
    def get_models(cls) -> list[Type[DocType]]:
        """ Returns a list of MongoDB Beanie document classes as specified in the `models` module"""
        return [doc for _, doc in getmembers(sys.modules[__name__], isclass)
                if issubclass(doc, Document) and doc.__name__ != "Document"]

    @classmethod
    async def init_db(cls, hostname: str = "localhost", port: int = 27017, db_name: str = "",
                      username: str = "", password: str = "", params: str = "", mongo_base: str = "mongodb"):
        """

        @param hostname: database hostname
        @param port: database port
        @param db_name: database name
        @param username: database username
        @param password: database password
        @param params: database params

        @return AsyncIOMotorDatabase
        @param mongo_base: MongoDB database
        """
        connection_string = f'mongodb://{hostname}:{port}/{db_name}'
        if hostname != 'localhost' and password:
            connection_string = f'{mongo_base}://{username}:{password}@{hostname}/{db_name}?{params}'
        # print(connection_string)
        client = AsyncIOMotorClient(connection_string)
        document_models = cls.get_models()
        # print("-----------", connection_string)
        cls.db = await init_beanie(database=client[db_name], document_models=document_models)
