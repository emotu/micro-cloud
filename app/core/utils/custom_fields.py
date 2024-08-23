from datetime import datetime, timezone, timedelta, date, time
from typing import Any, Annotated, TypeVar

import jwt
from beanie import PydanticObjectId
from bson import ObjectId
from pydantic import BaseModel, Field, computed_field, AfterValidator, PlainSerializer
from pydantic_extra_types.country import CountryAlpha2
from pydantic_extra_types.phone_numbers import PhoneNumber

from app.config import settings
from app.core.utils.enums import RouteTypes

T = TypeVar("T", str, PydanticObjectId)

# Field configurations that will be shared across multiple models throughout the project
# TODO: Convert custom fields into subclasses that also handle serialization
PhoneNumber.phone_format = "E164"


def check_object_id(value: Any) -> Any:
    """ Validation checker and converter for ObjectId in query parameters"""
    if PydanticObjectId.is_valid(value):
        return PydanticObjectId(value)
    return value


def _check_list_values(values: list[Any]) -> list[Any]:
    return [check_object_id(v) for v in values]


def serialize_if_object_id(value: Any) -> Any:
    """ Simple serializer used to convert ObjectId in query params back to strings """
    if isinstance(value, (PydanticObjectId, ObjectId)):
        return str(value)
    return value


def convert_to_datetime(dt: date | datetime) -> datetime:
    """ Converts a date or datetime object to a datetime object"""
    if isinstance(dt, date):
        return datetime.combine(dt, time())
    return dt


# CountryStr = Annotated[CountryAlpha2, PlainSerializer(lambda v: v.short_name)]
CountryStr = CountryAlpha2

PhoneStr = PhoneNumber
AutoDateTime = Field(default_factory=lambda: datetime.now(timezone.utc))

DateTimeStr = Annotated[date | datetime, AfterValidator(convert_to_datetime)]

# Will be used as a reference field type for coercion, de-serialization and serialization
# TODO: Convert this into a function to enable you pass Field attributes into it
ReferenceField = Annotated[
    PydanticObjectId | str,
    AfterValidator(check_object_id),
    PlainSerializer(serialize_if_object_id)
]


class AuthToken(BaseModel):
    """model to hold and validate jwt user claim"""
    uid: str
    # iss: str = settings.JWT_ISSUER_CLAIM
    exp: datetime = Field(default_factory=lambda: datetime.now() + timedelta(hours=settings.JWT_EXPIRES_IN_HOURS))

    @property
    def token(self) -> str:
        """ Generate the JWT using the data from the model object"""
        data = self.model_dump()
        return jwt.encode(data, key=settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM).encode("utf-8")

    @classmethod
    def get_user_id(cls, token) -> str | None:
        """ Parse the token, and extract the uid"""
        data = jwt.decode(token, key=settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        validated = cls.model_validate(data)
        return validated.uid


class AppToken(BaseModel):
    """
    Model to validate and convert values to and from jwt token
    """

    key: str
    app_id: str
    # instance_id: PydanticObjectId | str
    entity_id: PydanticObjectId | str | None = None
    user_id: PydanticObjectId | str | None = None

    @computed_field
    def live_mode(self) -> bool:
        return True if self.key.startswith("sk_live") else False


def format_validation_error(*, key: str | None = "", type:str | None = "unknown_err", message: str):

    return [dict(
        type=type,
        loc= ["body",key],
        msg=message,
    )]




class ExtraParameters(BaseModel):
    # instance_id: ReferenceField | None = None
    # user: ReferenceField | None = None
    entity_id: ReferenceField | None = None
    user_id: ReferenceField | None = None
    token: AppToken | None = None
    live_mode: bool | None = False
    route_type: RouteTypes = RouteTypes.APP

    def as_dict(self):
        if self.route_type == RouteTypes.API and self.token is not None:
            return self.token.model_dump(exclude={"key"})
        return self.model_dump(exclude={"app_id", "route_type"})

    def as_obj(self):
        if self.route_type == RouteTypes.API and self.token is not None:
            return ExtraParameters.model_validate(self.token.model_dump(exclude={"key"}))
        return ExtraParameters.model_validate(self.model_dump(exclude={"app_id", "route_type"}))

