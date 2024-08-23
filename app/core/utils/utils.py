import random
from pprint import pprint
import requests
import unicodedata
import re
import string

from jinja2 import Environment, BaseLoader


def make_rest_request(url, data=None, method_name="post", **kwargs):
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
        pprint(headers)
        pprint(params)
        pprint(data)

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
        return resp_data
    except Exception as e:
        print(e)
        res.update(message=str(e))

    return res


def slugify(text):
    # Convert text to lowercase and replace spaces with hyphens
    text = text.lower().replace(" ", "-")

    # Remove special characters, accents, and symbols
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("utf-8")

    # Remove any remaining non-alphanumeric characters except hyphens
    text = re.sub(r"[^\w\s-]", "", text)

    # Remove multiple hyphens and leading/trailing hyphens
    text = re.sub(r"[-\s]+", "-", text).strip("-")

    return text

def slugify_with_exclude(text, excluded_char=None):
    # Convert text to lowercase and replace spaces with hyphens
    text = text.lower().replace(" ", "-")

    # Remove special characters, accents, and symbols excluding the specified character
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("utf-8")
    text = re.sub(fr"[^\w\s{re.escape(excluded_char)}-]", "", text) if excluded_char \
        else re.sub(r"[^\w\s-]", "", text)

    # Remove multiple hyphens and leading/trailing hyphens
    text = re.sub(r"[-\s]+", "-", text).strip("-")

    return text


def token_generator(size=8, chars=string.digits):
    """
    utility function to generate random identification numbers
    """
    return ''.join(random.choice(chars) for x in range(size))


def format_template(template: str, payload: dict):
    """
    Create the actual content to be sent by replacing the placeholder texts in
    the template with corresponding value extracted from the payload
    """
    print(f"{'-' * 40}PARSING{'-' * 40} ")
    parser = Environment(loader=BaseLoader()).from_string(template)
    content = parser.render(**payload)
    return content
