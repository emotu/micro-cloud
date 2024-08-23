from app.models import NotificationEvent


class NotificationEventService(NotificationEvent):

    """"""

    def prepare_send_data(self, event=None):
        """
        extract and organise data from the event object
        @return: dict
        """
        event = self.event if not event else event
        subject = event.subject_template
        recipient = event.recipient
        content = event.content
        user_id = event.target_id
        payload = event.payload
        bcc = event.bcc
        cc = event.cc
        # instance_id = event.instance_id
        code = event.code
        email_sender_id = event.email_sender_id
        is_broadcast = event.is_broadcast
        thread_id = event.thread_id
        return dict(subject=subject, recipient=recipient, content=content, user_id=user_id,
                    payload=payload, code=code, cc=cc, bcc=bcc, email_sender_id=email_sender_id,
                    is_broadcast=is_broadcast, thread_id=thread_id)
