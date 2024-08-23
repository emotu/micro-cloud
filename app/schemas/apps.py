from beanie import PydanticObjectId
from pydantic import BaseModel


class ApplicationSchema(BaseModel):
    name: str
    description: str | None = None

    test_webhook: str | None = None
    live_webhook: str | None = None

    test_wallet_id: PydanticObjectId | str | None = None
    live_wallet_id: PydanticObjectId | str | None = None


class ResetApplicationSchema(BaseModel):
    test_mode: bool = False
    live_mode: bool = False
