from datetime import datetime, date, timezone, timedelta
from typing import Annotated, Optional, Literal

import holidays
from beanie import Document, Indexed, Insert, Replace, Update, before_event, PydanticObjectId, Link, Save
from pydantic import BaseModel, EmailStr, computed_field, ConfigDict, PositiveFloat, PositiveInt, field_validator
from pydantic_extra_types.coordinate import Longitude, Latitude

from app.config import settings
# from app.core.connectors import  livigston
# from app.core.connectors.loqate import Loqate
from app.core.utils.custom_fields import AutoDateTime, PhoneStr, CountryStr, ReferenceField
from app.core.utils.enums import Statuses, EtaWindows
from app.core.utils.generators import generate_alpha_id


class AppMixin(BaseModel):
    """
    Model class to implement generally shared functionality like date_created and last_updated fields, including
    the event behavior that needs to be utilized across multiple models throughout the application.
    """

    # instance_id: Annotated[ReferenceField, Indexed()]
    app_id: str | None = None
    date_created: datetime = AutoDateTime
    last_updated: datetime = AutoDateTime
    live_mode: bool = False

    model_config = ConfigDict(str_strip_whitespace=True)

    # @computed_field
    # def pk(self) -> PydanticObjectId | str:
    #     return self.id

    @before_event(Insert, Replace, Update)
    def _set_last_updated(self):
        self.last_updated = datetime.now(timezone.utc)


class AddressModel(BaseModel):
    """
    Basemodel type that forms address structure for embedded and saved addresses.
    """
    first_name: str | None = None
    last_name: str | None = None
    business_name: str | None = None
    email: EmailStr | str | None = None
    phone: PhoneStr | str | None = None
    street: str | None = None
    street_line_2: str | None = None
    city: str | None = None
    state: str | None = None
    post_code: str | None = None
    country: CountryStr
    lat: Latitude | None = None
    lng: Longitude | None = None

    @computed_field
    def name(self) -> str:
        if not self.first_name or not self.last_name:
            return None
        return " ".join([self.first_name, self.last_name])


class Address(AppMixin, Document, AddressModel):
    """"""


class Status(Document):
    name: str
    id: Indexed(str)
    # code: Optional[str] = None
    description: Optional[str] = None
