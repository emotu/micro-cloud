from datetime import date, datetime, timedelta
from typing import Annotated, Optional, Literal

import bcrypt
import pycountry
import pyotp
from beanie import Document, Indexed, PydanticObjectId, Link
from beanie.odm.operators.find.logical import Or
from pydantic import EmailStr, SecretStr, Field, field_serializer, computed_field, ConfigDict

from app.core.utils.custom_fields import CountryStr, PhoneStr, AutoDateTime, ReferenceField
from app.core.utils.enums import PermissionTypes, AccountTypes
from app.models import AppMixin


class User(Document):
    """
    Primary User model that holds user records within the database
    """

    model_config = ConfigDict(str_strip_whitespace=True)

    class Settings:
        use_cache = False
        cache_expiration_time = timedelta(seconds=60)
        use_revision = True

    first_name: Optional[str] = None
    last_name: Optional[str] = None

    country: CountryStr
    currency: str | None = "NGN"

    # instance_id: Annotated[PydanticObjectId | str, Indexed()]

    email: Annotated[EmailStr, Indexed(unique=True)]
    phone: Annotated[PhoneStr, Indexed(unique=True)]
    password: Annotated[str | SecretStr | None, Field(exclude=True)] = None

    is_suspended: Optional[bool] = False
    # is_notification_registered: Optional[bool] = False
    is_email_verified: Optional[bool] = False
    is_phone_verified: Optional[bool] = False

    requires_password_reset: Annotated[Optional[bool], Field(exclude=True)] = False
    migrated_entity: Annotated[Optional[bool], Field(exclude=True)] = False
    current_reset_hash: Annotated[Optional[bool], Field(exclude=True)] = False
    current_otp: Annotated[Optional[bool], Field(exclude=True)] = False
    is_2fa_enabled: bool | None = False

    otp2fa_secret: Annotated[Optional[str], Field(exclude=True, default_factory=pyotp.random_base32)]
    otp_provider: Literal["authenticator", "email", "phone", "default"] = "default"

    gender: Literal["male", "female", "unknown"] | None = "unknown"
    date_of_birth: Optional[date] = None
    website: Optional[str] = None
    photo: Optional[str] = None

    franchise_id: Optional[str] = None
    forwarding_id: Optional[str] = None

    last_logged_in: Optional[datetime] = None
    features: Optional[list[str]] = []

    account_type: AccountTypes | None = AccountTypes.PERSONAL

    date_created: datetime = AutoDateTime
    last_updated: datetime = AutoDateTime

    def custom_dict(self) -> dict:
        return dict(name=self.name, phone=self.phone,
                    email=self.email)

    @field_serializer('country', when_used="json-unless-none")
    def serialize_country(self, country: str):
        print("here", country)
        c = pycountry.countries.get(alpha_2=country)
        return dict(name=c.name, code=c.alpha_2)

    @computed_field
    def name(self) -> str:
        return f"{self.first_name.strip()} {self.last_name.strip()}"

    def set_password(self, password: str | bytes):
        """
        Internal method to set a password on a user before saving the user to the database.
        @param password: new password to be set
        @return: User object
        """
        self.password = (bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())).decode()

    def check_password(self, password) -> bool:
        """
        Check the password of the against the existing password in the database

        @param password: password to compare against
        @return: bool
        """

        if not password or not isinstance(password, (str, bytes)):
            raise ValueError("Password must be non-empty string or bytes value")
        password = password.encode('utf-8')

        # both password and hashed password need to be encrypted.
        return bcrypt.checkpw(password, self.password.encode('utf-8'))

    def generate_otp(self, interval=30, generate_key: str | None = None):
        """Generate an OTP code for authentication"""

        """
            REASON FOR GENERATE_KEY: I DON'T WANT THINGS LIKE PASSWORD RESET TO COME FROM THE USER 2FA
            FOR SECURITY REASON BECAUSE ANY ONE WITH THE BROWSER CAN EASILY RESET PASSWORD. I MIGHT BE WRONG
        """
        if generate_key:
            totp = pyotp.TOTP(generate_key + self.otp2fa_secret, interval=interval)
            return totp.now()
        totp = pyotp.TOTP(self.otp2fa_secret, interval=interval)
        return totp.now()

    def validate_otp(self, otp: str, generate_key: str | None = None) -> bool:
        """ Check the provided OTP input against the user's otp key"""

        """
                   REASON FOR GENERATE_KEY: I DON'T WANT THINGS LIKE PASSWORD RESET TO COME FROM THE USER 2FA
                   FOR SECURITY REASON BECAUSE ANY ONE WITH THE BROWSER CAN EASILY RESET PASSWORD. I MIGHT BE WRONG
               """
        if generate_key:
            totp = pyotp.TOTP(generate_key + self.otp2fa_secret)
            return totp.verify(otp)
        totp = pyotp.TOTP(self.otp2fa_secret)
        return totp.verify(otp)

    async def regenerate_2fa_secret(self):
        """ Regenerate the OTP secret key for a users account. """
        self.otp2fa_secret = pyotp.random_base32()
        await self.save()

    @classmethod
    async def check_user_exists(
            cls, email: str | EmailStr,
            phone: str | PhoneStr
    ) -> "User":
        """
        @param email: Email address to check
        @param phone: Phone number to check
        @param instance_id: Instance ID to check the user against.

        @return: exists (True|False)
        """

        print(phone, email)

        return await cls.find_one(
            Or(cls.email == email, cls.phone == phone),
            # cls.instance_id == instance_id
        )

    @classmethod
    async def find_by_username(cls, username: str | EmailStr | PhoneStr) -> "User":
        """

        @param username: Username to check email | phone number against.
        @param instance_id: Instance ID to check the user against.

        @return: exists (True|False)
        """

        return await cls.find_one(
            Or(cls.email == username, cls.phone == username),
            # cls.instance_id == instance_id
        )
