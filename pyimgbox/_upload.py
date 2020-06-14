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

import logging
import mimetypes
import os
import pprint

import bs4
import requests

from . import _const, _utils

log = logging.getLogger('pyimgbox')


class Submission(dict):
    """
    Dictionary with the following keys:

    success: True or False
    error: Error message or None
    name: File name or None
    path: File path or None
    image_url: URL to image or None
    web_url: URL to image's web page or None
    gallery_url: URL to web page of thumbnails or None
    edit_url: URL to manage gallery None
    """

    def __new__(cls, *, success, **kwargs):
        values = {
            'success': bool(success),
            'error': None,
            'filename': None,
            'filepath': None,
            'image_url': None,
            'thumbnail_url': None,
            'web_url': None,
            'gallery_url': None,
            'edit_url': None,
        }
        for k in kwargs:
            assert k in values, f'Unknown key: {k!r}'
        if not success:
            assert 'error' in kwargs, "Missing key: 'error'"
        else:
            assert 'error' not in kwargs, "Conflicting keys: 'error', 'success'"
            for k in ('filename', 'filepath', 'image_url', 'thumbnail_url',
                      'web_url', 'gallery_url', 'edit_url'):
                assert k in kwargs, f'Missing key: {k!r}'
        values.update(kwargs)
        return super().__new__(cls, values)

    def __repr__(self):
        kwargs = ', '.join(f'{k}={v!r}'
                           for k,v in self.items()
                           if v is not None)
        return f'{type(self).__name__}({kwargs})'


class Gallery():
    """
    Upload images to a gallery on imgbox.com

    title: Name of the Gallery
    comments_enabled: Whether comments are enabled for this gallery
    """

    def __init__(self, title=None, comments_enabled=False):
        self._title = str(title) if title else None
        self._comments_enabled = bool(comments_enabled)
        self._session = requests.Session()
        self._token = {}

    @property
    def title(self):
        """Name of the Gallery"""
        return self._title

    @property
    def comments_enabled(self):
        """Whether comments are enabled for this gallery"""
        return self._comments_enabled

    @property
    def _initialized(self):
        return bool(_const.CSRF_TOKEN_HEADER in self._session.headers and self._token)

    def _init(self):
        # Get CSRF token
        csrf_token = None
        text = _utils.get(self._session, f'https://{_const.SERVICE_DOMAIN}/', timeout=30)
        soup = bs4.BeautifulSoup(text, features="html.parser")
        log.debug(soup.prettify())
        # Find <meta content="..." name="csrf-token" />
        for meta in soup.find_all('meta', {'name': 'csrf-token'}):
            csrf_token = meta.get('content')
            log.debug('Found CSRF token: %s', csrf_token)
        if not csrf_token:
            raise RuntimeError("Couldn't find CSRF token in HTML head")
        else:
            self._session.headers.update({_const.CSRF_TOKEN_HEADER: csrf_token})

        # Get token_id / token_secret
        data = [
            ('gallery', 'true'),
            ('gallery_title', self._title or ''),
            ('comments_enabled', '1' if self._comments_enabled else '0'),
        ]
        token = _utils.post_json(self._session, _const.TOKEN_URL, data=data, timeout=30)
        if not isinstance(token, dict):
            raise RuntimeError(f'Not a dict: {token!r}')
        else:
            log.debug('Session request headers:\n%s', pprint.pformat(self._session.headers))
            self._token = token
            log.debug('Gallery token:\n%s', pprint.pformat(self._token))

    def _submit_file(self, filepath, content_type, thumbnail_size, timeout):
        submission = {'filename': os.path.basename(filepath),
                      'filepath': filepath}

        try:
            fileobj = open(filepath, 'rb')
        except OSError as e:
            return Submission(success=False, error=e.strerror, **submission)

        mimetype = mimetypes.guess_type(filepath)[0]
        if not mimetype:
            return Submission(success=False,
                              error='Unknown mime type',
                              **submission)
        if mimetype not in _const.ALLOWED_MIMETYPES:
            return Submission(success=False,
                              error=f'Unsupported file type: {mimetype}',
                              **submission)

        data = [
            ('token_id', self._token['token_id']),
            ('token_secret', self._token['token_secret']),
            ('content_type', content_type),
            ('thumbnail_size', thumbnail_size),
            ('gallery_id', self._token.get('gallery_id', 'null')),
            ('gallery_secret', self._token.get('gallery_secret', 'null')),
            ('comments_enabled', '1' if self._comments_enabled else '0'),
        ]
        files = [('files[]', (os.path.basename(filepath),
                              fileobj,
                              mimetype))]
        try:
            json = _utils.post_json(self._session, _const.PROCESS_URL,
                                    data=data, files=files, timeout=timeout)
        except OSError as e:
            # Raised when connection fails or fileobj.read() fails
            return Submission(success=False, error=str(e), **submission)
        except ValueError as e:
            # Raised when remote side returns non-JSON
            return Submission(success=False, error=str(e), **submission)

        log.debug('POST response:\n%s', pprint.pformat(json))
        if 'files' not in json:
            raise RuntimeError(f"Unexpected response: Couldn't find 'files': {json}")
        elif not isinstance(json['files'], list):
            raise RuntimeError(f"Unexpected response: 'files' is not a list: {json}")
        elif not json['files']:
            raise RuntimeError(f"Unexpected response: 'files' is empty: {json}")

        info = json['files'][0]
        return Submission(
            success=True,
            filename=os.path.basename(filepath),
            filepath=filepath,
            image_url=info['original_url'],
            thumbnail_url=info['thumbnail_url'],
            web_url=info['url'],
            gallery_url=_const.GALLERY_URL_FORMAT.format(**self._token),
            edit_url=_const.EDIT_URL_FORMAT.format(**self._token),
        )

    def submit(self, *filepaths, nsfw=False, thumb_width=100, square_thumbs=False, timeout=None):
        """
        Generator that uploads images and yields dictionaries with URLs

        filepaths: Iterable of file paths to images
        nsfw: True if any images are adult content, False otherwise
        thumb_width: Thumbnail width in pixels; will automoatically snap to closest
                     supported value
        square_thumbs: True to make thumbnails square, False otherwise
        timeout: Number of seconds of no sign of life before giving up

        Yield Submission objects.
        """
        if not filepaths:
            return
        elif not self._initialized:
            try:
                self._init()
            except (OSError, ValueError) as e:
                yield Submission(success=False, error=str(e))
                return

        content_type = (_const.CONTENT_TYPES['adult'] if nsfw
                        else _const.CONTENT_TYPES['family'])

        if square_thumbs:
            thumbnail_widths = _const.THUMBNAIL_WIDTHS_SQUARE
        else:
            thumbnail_widths = _const.THUMBNAIL_WIDTHS_KEEP_ASPECT
        thumbnail_width = thumbnail_widths[
            _utils.find_closest_number(thumb_width, thumbnail_widths)]

        for filepath in filepaths:
            yield self._submit_file(filepath, content_type, thumbnail_width, timeout=timeout)

    def __repr__(self):
        return (f'{type(self).__name__}('
                f'title={repr(self._title)}, '
                f'comments_enabled={repr(self._comments_enabled)})')
