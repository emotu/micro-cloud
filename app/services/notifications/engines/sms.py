"""
@author : Maro Okegbero
@date : 29 Nov 2021
"""
from pydantic import BaseModel

from app.config import settings
from app.core.messaging.africastalking.sms import SMS
from app.core.messaging.twilio.sms import TwilioSMS, SMSSendRequest


class SmsInput(BaseModel):
    message: str
    recipient: str


class SmsResponse(BaseModel):
    status: str
    message: str


class SmsEngine:
    @classmethod
    def send_notification(cls, data: SmsInput):
        """
        sends the notification as  sms
        """
        print(f"{'*' * 40}SENDING SMS NOTIFICATION{'*' * 40} ")
        recipient = data.recipient
        message = data.message
        try:
            provider = cls.get_provider(recipient)
            data = SMSSendRequest(message=message, numbers=[recipient])
            provider.send(data)
            print(f"{'*' * 40} SMS REPORT: SENT SUCCESSFULLY{'*' * 40} ")
            return SmsResponse(status="successful", message="Sent")

        except Exception as e:
            print(f"{'*' * 40}SMS REPORT: ERROR FROM PROVIDER > {e, '*' * 40} ")
            return SmsResponse(status="failed", message=str(e))

    @classmethod
    def get_provider(cls, recipient):
        """
        determines which provider to use based on the recipient country code
        @param recipient:
        @return:
        """
        code = recipient[:4]

        api_key = settings.AT_SMS_API_KEY
        username = settings.AT_SMS_USERNAME
        sender_id = settings.AT_SMS_SENDER_ID

        if code in ["+234", "+233", "+254"]:
            return SMS(username=username, api_key=api_key, sender_id=sender_id)

        return TwilioSMS(settings.TWILIO_SID, settings.TWILIO_AUTH_TOKEN, settings.TWILIO_SENDER_ID)
