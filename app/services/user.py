from app.models import User


class UserService(User):

    """"""
    @classmethod
    def register_account(cls, user_class, **kwargs):
        """"""

    @classmethod
    def deactivate_user(cls, **kwargs):
        """"""

    @classmethod
    def convert_account(cls, user_class, **kwargs):
        """"""

    @classmethod
    def verify_email(cls, **kwargs):
        """"""

    @classmethod
    def verify_phone(cls, **kwargs):
        """"""

    @classmethod
    def reset_password(cls, obj_id, **kwargs):
        """"""

    @classmethod
    def update_history(cls, user_id, **kwargs):
        """"""

    @classmethod
    def request_update_email(cls, obj_id, **kwargs):
        """"""

    @classmethod
    def update_email(cls, obj_id, **kwargs):
        """"""

    @classmethod
    def request_update_phone(cls, obj_id, **kwargs):
        """"""

    @classmethod
    def update_phone(cls, obj_id, **kwargs):
        """"""

    @classmethod
    def request_password(cls, **kwargs):
        """"""

    @classmethod
    def request_password_phone(cls, **kwargs):
        """"""

    @classmethod
    def resend_otp(cls, **kwargs):
        """"""

    @classmethod
    def find_user(cls, **kwargs):
        """"""

    @classmethod
    def generate_2fa_secret(cls, obj_id):
        """
        Generate the secret key for 2FA validation using TOTP (Time based OTP)
        :param obj_id:
        :return:
        """



    @classmethod
    def request_otp(cls, **kwargs):
        """

        """

    @classmethod
    def validate_otp(cls, **kwargs):
        """

        """



    @classmethod
    def generate_forwarding_id(cls, user_id, false_forwarding_id=None):
        """

        """