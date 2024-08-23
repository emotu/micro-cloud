import base64
from datetime import datetime, date, timedelta, timezone
from typing import Annotated, Optional, Any

import bcrypt
import pycountry
import pymongo
from beanie import Document, Indexed, Link, PydanticObjectId, before_event, Insert, Replace, Update
from beanie.operators import Or
from fastapi import HTTPException
from pydantic import ConfigDict
from pydantic import Field, EmailStr, SecretStr, computed_field, HttpUrl, field_serializer, BaseModel
from pydantic_extra_types.coordinate import Latitude, Longitude
from pymongo import IndexModel
from starlette import status

from app.config import settings
from app.core.utils.custom_fields import AutoDateTime, ReferenceField
from app.core.utils.generators import generate_secret_key, generate_id
from app.models.shared import AppMixin, PhoneStr, CountryStr, AddressModel


class BusinessType(Document):
    """ Types of business registration, based on country"""
    code: Annotated[str, Indexed()]
    name: str
    country: CountryStr
    description: Optional[str] = None

    # @before_event(Insert, Replace, Update)
    # def _auto_assign(self):
    #     self.code = " ".join([self.first_name, self.last_name])


class Address(AppMixin, Document, AddressModel):
    """ Saved address model for users and entities """
    entity: Annotated[Link["Business"] | None, Field(exclude=False, validation_alias="entity_id")] = None
    user: Annotated[Link["User"] | None, Field(exclude=False, validation_alias="user_id")] = None


class ApiCredential(Document):
    """
    NOTE: Does not inherit from AppMixin because certain keys (app_id, live_mode) are not relevant here.

    3rd party application with API credentials.
    This will be used to define and provide access credentials to integration platforms wishing to access functionality
    from their accounts on third party platforms.
    """
    model_config = ConfigDict(str_strip_whitespace=True, validate_default=True, validate_assignment=True)

    class Settings:
        use_cache = False
        cache_expiration_time = timedelta(seconds=10)
        cache_capacity = 100
        validate_on_save = True

    name: str
    description: str | None = None

    entity_id: Annotated[ReferenceField | None, Field(exclude=False), Indexed()] = None
    user_id: Annotated[ReferenceField | None, Field(exclude=False), Indexed()] = None
    # instance_id: Annotated[ReferenceField | None, Field(exclude=False), Indexed()]

    app_id: Annotated[str, Field(default_factory=generate_id), Indexed(str, unique=True)]

    test_key: Annotated[
        str | None,
        Field(default_factory=lambda: generate_secret_key(test=True)),
        Indexed(unique=True)
    ]
    test_webhook: HttpUrl | None = None
    test_wallet_id: PydanticObjectId | str | None = None

    live_key: Annotated[
        str | None,
        Field(default_factory=lambda: generate_secret_key(test=False)),
        Indexed(unique=True)
    ]
    live_webhook: HttpUrl | None = None
    live_wallet_id: PydanticObjectId | str | None = None

    is_active: bool | None = True

    date_created: datetime = AutoDateTime
    last_updated: datetime = AutoDateTime

    @before_event(Insert, Replace, Update)
    def _set_last_updated(self):
        self.last_updated = datetime.now(timezone.utc)

    async def reset_credentials(self, test_mode: bool = False, live_mode: bool = True):
        """
        Resets the application credentials by regenerating the secret key and using it to regenerate the token
        :param test_mode: [bool] If true, will reset the test credentials
        :param live_mode: [bool] If true, will reset the live credentials
        :return:
        """

        if test_mode:
            self.test_key = generate_secret_key(test=True)

        if live_mode:
            self.live_key = generate_secret_key(test=False)

        await self.save()

    async def toggle_active(self):
        """
        Toggles the active state of the application
        :return:
        """
        self.is_active = not self.is_active
        await self.save()

    @classmethod
    async def find_by_key(cls, key: str) -> "ApiCredential":
        """ Find an application by the given api key. Returns None if no application is found """
        target = "live_key" if key.startswith("sk_live") else "test_key"
        target_query = dict([(target, key)])

        return await cls.find_one(target_query)
