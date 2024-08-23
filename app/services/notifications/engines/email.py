"""
@author : Maro Okegbero
@date : 29 Nov 2021
"""
from app.config import settings
from app.core.messaging.email import Postmark, EmailPayload, EmailResponse

from typing import List, Optional
from pydantic import BaseModel, EmailStr


class EmailPayloadAttachment(BaseModel):
    file_name: str
    content: str
    content_type: str


class SendEmailNotificationData(BaseModel):
    thread_id: Optional[str] = None
    email_sender_id: Optional[str] = None
    content: str
    recipient: EmailStr
    bcc: Optional[EmailStr] = None
    cc: Optional[EmailStr] = None
    subject: str
    attachments: Optional[List[EmailPayloadAttachment]] = []


class EmailEngine:

    @classmethod
    def send_notification(cls, data: SendEmailNotificationData) -> 'EmailResponse':
        """
        sends the notification as an email
        """
        print(f"{'-' * 40}SENDING EMAIL NOTIFICATION{'-' * 40} ")
        server_key = settings.POSTMARK_SERVER_KEY
        sender = settings.POSTMARK_SENDER if not data.email_sender_id else data.email_sender_id
        postmark = Postmark(server_key=server_key)

        # get the path of the email html template and parse it with the variables to get the html  text
        html = data.content
        email_data = {
            'from_': sender,
            'to': data.recipient,
            'bcc': data.bcc,
            'cc': data.cc,
            'subject': data.subject,
            'html': html,
            'attachments': data.attachments,
        }

        if data.thread_id:
            inbound_email = settings.POSTMARK_INBOUND_EMAIL_ADDRESS
            reply_email = inbound_email.replace('@', f'+{data.thread_id}@')
            email_data['reply_to'] = reply_email

        send_data = EmailPayload(**email_data)

        return postmark.send(send_data)

