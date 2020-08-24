import requests

from . import _const

import logging  # isort:skip
log = logging.getLogger('pyimgbox')


def get(session, url, timeout=None, **kwargs):
    log.debug('GET: %s: %s', url, kwargs)
    try:
        return session.get(url, timeout=timeout or _const.DEFAULT_TIMEOUT, **kwargs).text
    except requests.exceptions.RequestException:
        raise ConnectionError(f'Failed to connect to {_const.SERVICE_DOMAIN}')


def post_json(session, url, timeout=None, **kwargs):
    log.debug('POST: %s: %s', url, kwargs)
    try:
        response = session.post(url, timeout=timeout or _const.DEFAULT_TIMEOUT, **kwargs)
    except requests.exceptions.RequestException:
        raise ConnectionError(f'Failed to connect to {_const.SERVICE_DOMAIN}')
    else:
        log.debug('Response text for %s: %r', url, response.text)
        if response.status_code == 413:
            raise ConnectionError('File is too large')
        else:
            try:
                return response.json()
            except ValueError as e:
                raise ValueError(f'{e}: {response.text}')


def find_closest_number(n, ns):
    # Return the number from `ns` that is closest to `n`
    return min(ns, key=lambda x: abs(x - n))
