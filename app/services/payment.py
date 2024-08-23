from app.core.utils.enums import Statuses
from app.models import Account, validate_transaction_action, Checkout, Transaction, Card
from app.schemas.quote import ValidateTransactionSchema
from app.services import UssdService


class PaymentService:


    @classmethod
    async def validate_transaction(cls, checkout_id: str,txRef: str | None = None):
        """"""

        checkout = await Checkout.get(checkout_id)

        print("validate_transaction")
        transaction = await Transaction.find_one({"checkout_reference": checkout.code,
                                                  "transaction_reference": txRef})
        print("payment method", transaction.payment_method)
        if transaction.status == Statuses.COMPLETED:
            return transaction
        if transaction.payment_method in ["card", "virtual"]:
            print("payment method")
            data = dict(amount=transaction.amount, reference=txRef)
            payload = ValidateTransactionSchema.model_validate(data)
            response = await Card.validate_transaction(str(transaction.id), str(checkout.id), payload)
            transaction.transaction_reference = response.txref
            transaction.status = response.status
            transaction.narration = response.message
            await transaction.save()
            print("response.status", response.status)
            if response.status == Statuses.COMPLETED:
                await transaction.fetch_all_links()
                credit_account_id = transaction.account.id
                credit_account = await Account.get(credit_account_id)
                cred_trans = await credit_account.credit(payment_method=transaction.payment_method,
                                                         source=transaction.source,
                                                         amount=transaction.amount,
                                                         reference_code=transaction.reference,
                                                         transaction_reference=transaction.transaction_reference,
                                                         checkout_reference=transaction.checkout_reference,
                                                         product_type=transaction.product_type)
                checkout.status = response.status
                checkout.narration = response.message
                checkout.transaction_reference = response.txref
                await checkout.save()
                transaction.status = response.status
                transaction.narration = response.message
                await transaction.save()
                await validate_transaction_action(checkout.product_type, checkout.reference, str(checkout.id))
                return transaction
        if transaction.payment_method in ["ussd"]:
            data = dict(amount=transaction.amount, reference=txRef)
            payload = ValidateTransactionSchema.model_validate(data)
            response = await UssdService.validate_transaction(str(transaction.id), str(checkout.id))
            transaction.transaction_reference = response.txref
            transaction.status = response.status
            transaction.narration = response.message
            await transaction.save()
            print("response.status", response.status)
            if response.status == Statuses.COMPLETED:
                await transaction.fetch_all_links()
                credit_account_id = transaction.account.id
                credit_account = await Account.get(credit_account_id)
                cred_trans = await credit_account.credit(payment_method=transaction.payment_method,
                                                         source=transaction.source,
                                                         amount=transaction.amount,
                                                         reference_code=transaction.reference,
                                                         transaction_reference=transaction.transaction_reference,
                                                         checkout_reference=transaction.checkout_reference,
                                                         product_type=transaction.product_type)
                checkout.status = response.status
                checkout.narration = response.message
                checkout.transaction_reference = response.txref
                await checkout.save()
                transaction.status = response.status
                transaction.narration = response.message
                await transaction.save()
                await validate_transaction_action(checkout.product_type, checkout.reference, str(checkout.id))
                return transaction