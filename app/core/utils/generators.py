"""
generators.py


Helper functions to generate API credentials, secret keys and unique Ids.
"""
import hashlib
import string
import time
from random import random
import jwt
import bcrypt
import shortuuid
import secrets


def generate_id(length=16) -> str:
    """
    Generate API Key
    :return: str -> generated API key for 3rd party API applications.
    """
    shortuuid.set_alphabet(string.ascii_letters + string.digits)
    return shortuuid.random(length=length)


def generate_numeric_id(length=8, fill=10, prefix="", chars=string.digits):
    """
    Generate a numeric code / id for use as tracking or order numbers
    """
    shortuuid.set_alphabet(chars)
    return "".join([prefix, shortuuid.random(length=length).zfill(fill)])

def generate_alpha_id(length=8, fill=0, prefix="", chars=string.ascii_letters):
    """
    Generate a numeric code / id for use as tracking or order numbers
    """
    shortuuid.set_alphabet(chars)
    return "".join([prefix, shortuuid.random(length=length).zfill(fill)])


def generate_secret_key(test: bool) -> str:
    """
        Generate App ID using a secrets pattern. If needed, expand the logic to contain more security.
        :return: str -> generated API ID for 3rd party API applications.
        """

    prefix = "sk_test" if test is True else "sk_live"

    return "_".join([prefix, str(secrets.token_urlsafe())])


def encrypt_secret_key(secret_key: str) -> str:
    """
    Encrypt the secret key to be used in 3rd party API applications
    :param secret_key: [str] The secret key to be encrypted
    :return: [str] The encrypted secret key
    """
    return bcrypt.hashpw(secret_key.encode(), bcrypt.gensalt()).decode()


def check_secret_key(secret_key: str, encrypted_secret_key: str) -> bool:
    """
    Check if the secret key matches the token provided
    :param secret_key:
    :param encrypted_secret_key: [str] The encrypted secret to check against
    :return:
    """

    return bcrypt.checkpw(secret_key.encode(), encrypted_secret_key.encode())
