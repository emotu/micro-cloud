"""
@author : Maro Okegbero
@date : 29 Nov 2021
"""
from pydantic import BaseModel

from app.config import settings
from app.core.messaging.twilio import Twilio


class WhatsappInput(BaseModel):
    message: str
    recipient: str


class WhatsappResponse(BaseModel):
    status: str
    message: str


country_code_dict = {
    "+234": "NG",
    "+233": "GH",
    "+254": "KE",
    "234": "NG",
    "233": "GH",
    "254": "KE",
}


class WhatsappEngine:
    @classmethod
    def send_notification(cls, data: WhatsappInput):
        """
        sends the notification as via whatsapp
        """
        try:
            twilio = Twilio(settings.TWILIO_SID, settings.TWILIO_AUTH_TOKEN, settings.TWILIO_SENDER_ID)

            twilio.whatsapp.send(data.message, [data.recipient])
            print(f"{'*' * 40} WHATSAPP REPORT: SENT SUCCESSFULLY{'*' * 40} ")
            return WhatsappResponse(status="successful", message="Sent")
        except Exception as e:
            print(f"{'*' * 40}WHATSAPP REPORT: ERROR FROM PROVIDER > {e, '*' * 40} ")
            return WhatsappResponse(status="failed", message=str(e))
