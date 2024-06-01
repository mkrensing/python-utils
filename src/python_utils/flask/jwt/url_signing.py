from functools import wraps
from mohawk.base import Resource
from mohawk.bewit import get_bewit, check_bewit
import time
import flask
import copy
import random
import string


def generate_random_key():
    return f"{generate_random_key_fragment()}{{context}}{generate_random_key_fragment()}{{context}}{generate_random_key_fragment()}{{context}}{generate_random_key_fragment()}"


def generate_random_key_fragment(length=20):
    return ''.join(random.SystemRandom().choice(get_chars_for_key()) for _ in range(length))


def get_chars_for_key():
    return string.printable.replace("{", "").replace("}", "")


credentials_template = {
    'id': 'JWT-URL-SIGNING-{context}',
    'key': generate_random_key(),
    'algorithm': 'sha256',
}


def create_credentials_for_context(context):
    credentials_for_context = copy.copy(credentials_template)
    credentials_for_context['id'] = credentials_for_context['id'].format(context=context)
    credentials_for_context['key'] = credentials_for_context['key'].format(context=context)

    return credentials_for_context


def make_credential_lookup(credentials_map):
    # Helper function to make a lookup function given a dictionary of
    # credentials
    def lookup(client_id):
        # Will raise a KeyError if missing; which is a subclass of
        # LookupError
        return credentials_map[client_id]

    return lookup


def sign_url(url, context, validity_period_in_seconds=10):

    res = Resource(url=url,
                   method='GET', credentials=create_credentials_for_context(context),
                   timestamp=int(time.time()) + int(validity_period_in_seconds),
                   nonce='')

    bewit = get_bewit(res)

    return f"{url}?bewit={bewit}"


def check_url(url_with_bewit, context):

    credentials = create_credentials_for_context(context)
    credential_lookup = make_credential_lookup({
        credentials['id']: credentials
    })

    return check_bewit(url_with_bewit, credential_lookup=credential_lookup)


def create_signed_url(access_control_function, parameter_name = "url", validity_period_in_seconds=10):
    context = access_control_function.__name__

    def wrapper(fn):
        @wraps(fn)
        def decorator(*args, **kwargs):
            url = flask.request.args.get(parameter_name)

            if not url:
                flask.abort(400)
                return

            signed_url = sign_url(url, context, validity_period_in_seconds)
            return fn(signed_url, *args, **kwargs)
        return decorator
    return wrapper


def signed_url_required(access_control_function):
    context = access_control_function.__name__

    def wrapper(fn):
        @wraps(fn)
        def decorator(*args, **kwargs):
            bewit = flask.request.args.get('bewit')

            if not bewit:
                flask.abort(403)
                return

            url = flask.request.full_path
            if not check_url(url, context=context):
                flask.abort(403)
                return

            return fn(*args, **kwargs)
        return decorator
    return wrapper

