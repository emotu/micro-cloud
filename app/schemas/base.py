"""
base.py

Input and response schemas that will be shared across different forms.
"""

from pydantic import BaseModel, EmailStr, ConfigDict, computed_field
from pydantic_extra_types.coordinate import Latitude, Longitude

from app.core.utils.custom_fields import PhoneStr, CountryStr


class BaseSchema(BaseModel):
    """ Base schema to inherit configuration from for all input and output forms"""
    model_config = ConfigDict(str_strip_whitespace=True)


class EmptySchema(BaseSchema):
    """"""


class AddressInput(BaseSchema):
    """ Input schema to accept address information """
    first_name: str
    last_name: str
    business_name: str | None = None
    email: EmailStr | None = None
    phone: PhoneStr
    street: str
    street_line_2: str | None = None
    city: str
    state: str
    post_code: str | None = None
    country: CountryStr
    lat: Latitude | None = None
    lng: Longitude | None = None

    @computed_field
    def name(self) -> str:
        return " ".join([self.first_name, self.last_name])