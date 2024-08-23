from typing import Optional, Literal
from pydantic import BaseModel, EmailStr, field_validator, ValidationInfo

from app.core.utils.custom_fields import ReferenceField
from app.core.utils.enums import AccountTypes
from app.models import CountryStr, PhoneStr
from app.schemas.base import BaseSchema


class AdminSignupRequest(BaseSchema):
    first_name: str
    last_name: str
    country: str
    email: EmailStr
    phone: PhoneStr
    role: str
    permissions: list[str]


class SignupRequest(BaseSchema):
    """
    Model that will be used to register a new user, validate the input before creating a user object in the database.
    """

    first_name: str
    last_name: str
    country: str
    email: EmailStr
    phone: PhoneStr
    password: str
    account_type: AccountTypes | None = AccountTypes.PERSONAL
    verify_password: str
    referral_code: Optional[str] | None = None

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "first_name": "John",
                    "last_name": "Doe",
                    "country": "NG",
                    "email": "john.doe@sendbox.co",
                    "phone": "+234810222228",
                    "password": "sendboxTest123",
                    "verify_password": "sendboxTest123",
                    "referral_code": "223453 (optional)"
                }
            ]
        }
    }

    @field_validator("verify_password", mode="after")
    def _validate_verify_password(cls, v: str, info: ValidationInfo):
        """ Validate info before storing passing along"""
        password = info.data.get("password")
        if password != v:
            raise ValueError("verify_password does not match password")

        return v


class LoginRequest(BaseSchema):
    """Login model """

    username: EmailStr | PhoneStr | str
    password: str
    otp: str | None = None

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "username": "(it could be either username, phone or email)",
                    "password": "Doe",
                    "otp": " (this is required if the person has otp required set to true)"
                }
            ]
        }
    }


class AuthBusinessResponse(BaseSchema):
    id: ReferenceField
    name: str | None = None
    domain: str | None = None
    country: CountryStr | None = None
    currency: str | None = None


class AuthResponse(BaseSchema):
    status: Literal["pending", "success", "needs_otp", "error", "failed"] = "success"
    id: ReferenceField
    # instance_id: ReferenceField
    token: str | None = None
    username: str | None = None
    email: EmailStr
    account_type: AccountTypes | None = AccountTypes.PERSONAL
    phone: PhoneStr | None = None
    first_name: str | None = None
    last_name: str | None = None
    country: CountryStr | None = None
    business: AuthBusinessResponse | None = None
    is_2fa_enabled: bool | None = None


class StatusCreateSchema(BaseSchema):
    id: str
    name: str
    description: Optional[str] = None


class StatusUpdateSchema(BaseSchema):
    name: str
    description: Optional[str] = None


class PasswordResetRequestSchema(BaseSchema):
    """Password reset request"""

    email: EmailStr
    domain: str

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "email": "john.doe@sendbox.co",
                    "domain": "Shipping",
                }
            ]
        }
    }


class PasswordResetResponseSchema(BaseSchema):
    status: str
    message: str


class PasswordResetSchema(BaseModel):
    code: str
    value: str
    password: str
    verify_password: str

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "code": "123456",
                    "password": "SendboxPassword123",
                    "verify_password": "SendboxPassword123",
                }
            ]
        }
    }

    @field_validator("verify_password", mode="before")
    def validate_passwords_match(cls, value, values):
        password = values.data.get("password")
        if password != value:
            raise ValueError("The passwords must match. Try again")
        return value
