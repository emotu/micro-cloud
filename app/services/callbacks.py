from app.core.connectors import LIVINGSTON, settings
from app.core.connectors.loqate import Loqate
from app.core.utils.enums import Statuses
from app.models import ShipmentRequest, Transaction, Card, Account, Checkout, validate_transaction_action
from app.schemas.quote import ValidateTransactionSchema
from app.services import UssdService


livingston = LIVINGSTON(settings=settings)





async def shipping_callback(reference_id: str,  checkout_id: str):
    return await ShipmentRequest.confirm_payment(reference_id, checkout_id)



#TODO:: CUSTOM SCHEMA ON COURIER MODEL.