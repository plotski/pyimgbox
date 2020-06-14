# This file is part of pyimgbox.
#
# This program is free software: you can redistribute it and/or modify it under the terms
# of the GNU General Public License as published by the Free Software Foundation, either
# version 3 of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
# PARTICULAR PURPOSE.  See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with this
# program.  If not, see <https://www.gnu.org/licenses/>.

import requests

from . import _const

import logging  # isort:skip
log = logging.getLogger('pyimgbox')


def get(session, url, timeout=None, **kwargs):
    log.debug('GET: %s: %s', url, kwargs)
    try:
        return session.get(url, timeout=timeout or _const.DEFAULT_TIMEOUT, **kwargs).text
    except requests.ConnectionError:
        raise ConnectionError(f'Failed to connect to {_const.SERVICE_DOMAIN}')


def post_json(session, url, timeout=None, **kwargs):
    log.debug('POST: %s: %s', url, kwargs)
    try:
        response = session.post(url, timeout=timeout or _const.DEFAULT_TIMEOUT, **kwargs)
    except requests.ConnectionError:
        raise ConnectionError(f'Failed to connect to {_const.SERVICE_DOMAIN}')
    else:
        log.debug('Response text for %s: %r', url, response.text)
        try:
            return response.json()
        except ValueError as e:
            raise ValueError(f'{e}: {response.text}')


def find_closest_number(n, ns):
    # Return the number from `ns` that is closest to `n`
    return min(ns, key=lambda x: abs(x - n))
