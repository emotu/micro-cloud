import json
from datetime import timedelta

from munch import DefaultMunch
from pprint import pprint
import requests
import string
import random
import re
from unicodedata import normalize
from math import ceil


def roundUp(n, d=2):
    """

    :param n:
    :param d:
    :return:
    """
    d = int('1' + ('0' * d))
    return ceil(n * d) / d


def calculate_exchange_rate(amount, currency, new_currency, ignore_redis=False):
    """

    :param amount:
    :type amount:
    :param amount:
    :param currency:
    :type currency:
    :param new_currency:
    :type new_currency:
    :param ignore_redis:
    :type ignore_redis:
    :return:
    :rtype:
    """

    # if currency == new_currency:
    #     return amount
    # excr_key = f"excr_{currency.lower()}"
    #
    # if ignore_redis:
    #     runt = rest_post(url=settings.FLUTTERWAVE_RATES_API, method_name="get",
    #                      params={"destination_currency": currency, "source_currency": new_currency, "amount": 1},
    #                      headers={"Authorization": f"Bearer {settings.FLUTTERWAVE_RATES_SECRET_KEY}"})
    #     currency_rate = runt.get("data", {}).get("rate")
    #     redis.setex(excr_key, timedelta(days=1), json.dumps({new_currency: currency_rate}))
    # return roundUp(float(currency_rate) * amount)


def munchify_dict(data: dict) -> DefaultMunch:
    return DefaultMunch(None, data)


def d_print(data, message: str = None) -> None:
    if message:
        print("====" * 5 + message + "====" * 5)
    pprint(data, indent=2)


def make_rest_request(url, data: dict = None, method_name: str = "post", **kwargs: dict) -> dict:
    """

    :param url:
    :param method_name:
    :param data:
    :param kwargs:
    :return:
    """

    res = dict(req_status='failed')
    try:
        headers = {"Content-Type": "application/json", "Cache-Control": "no-cache", "User-Agent": "python/sendbox-api"}

        headers.update(**kwargs.get("headers", {}))

        params = kwargs.get("params", {})

        print("sending infoo=====>", method_name)
        print(url)
        d_print(headers, url)
        d_print(params)
        d_print(data)

        if method_name == "get":
            resp = requests.get(url, headers=headers, params=params)
        elif method_name == "put":
            resp = requests.put(url, json=data, headers=headers)
        else:
            resp = requests.post(url, data=data, headers=headers)

        print(resp.status_code)

        print(resp.content)
        if "json" not in dir(resp):
            print(resp.content)

        resp_data = resp.json()

        resp_data.update(req_status='success', req_message="Success", req_status_code=resp.status_code)
        # pprint(resp_data)
        return munchify_dict(resp_data)
    except Exception as e:
        print(e)
        res.update(message=str(e))

    return res


def character_generator(size: int = 8, chars=string.ascii_letters.replace("o", "").replace("O", "")):
    """
    utility function to generate random identification numbers
    """
    return ''.join(random.choice(chars) for x in range(size))


def remove_empty_keys(data: dict) -> dict:
    """ removes None value keys from the list dict """
    res = {}

    for key, value in data.items():
        if value is not None:
            res[key] = value

    return res


def normalize_text(text):
    """
    Generates an ASCII-only text
    :rtype: str
    """
    if not text:
        return
    result = []
    for word in text:
        # ensured the unicode(word) because str broke the code
        word = re.sub(r'[^\x00-\x7f]', r'', word)
        word = normalize('NFKD', str(word)).encode('ascii', 'ignore')
        if word:
            word = word if isinstance(word, str) else word.decode("utf-8")
            result.append(word)
    return str(''.join(result))

