import logging
import mimetypes
import os

import bs4

from . import _const, _http, _utils
from ._submission import Submission

log = logging.getLogger('pyimgbox')


class Gallery():
    """
    Upload images to a gallery on imgbox.com

    title: Name of the Gallery
    adult: True if any images are adult content, False otherwise
    thumb_width: Thumbnail width in pixels; will automoatically snap to
                 nearest supported value
    square_thumbs: True to make thumbnails square, False otherwise
    comments_enabled: Whether comments are enabled for this gallery
    """

    def __init__(self, title=None, thumb_width=100, square_thumbs=False,
                 adult=False, comments_enabled=False):
        self._client = _http.HTTPClient()
        self._gallery_token = {}
        self.title = title
        self.square_thumbs = square_thumbs
        self.thumb_width = thumb_width
        self.adult = adult
        self.comments_enabled = comments_enabled

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self._client.close()

    @property
    def title(self):
        """
        Name of this gallery or None

        This property can not be changed after create() was called.
        """
        return self._title

    @title.setter
    def title(self, value):
        if self.created:
            raise RuntimeError('Gallery was already created')
        else:
            self._title = str(value) if value is not None else None

    @property
    def thumb_width(self):
        """Width of thumbnails for this gallery"""
        return getattr(self, '_thumb_width', 100)

    @thumb_width.setter
    def thumb_width(self, value):
        if not isinstance(value, (int, float)):
            raise ValueError(f'Not a number: {value!r}')
        self._thumb_width = _utils.find_closest_number(int(value), self._thumb_widths)
        self._thumbnail_width = self._thumb_widths[self._thumb_width]

    @property
    def square_thumbs(self):
        """Whether thumbnails have the same height and width"""
        return self._square_thumbs

    @square_thumbs.setter
    def square_thumbs(self, value):
        if value:
            self._square_thumbs = True
            self._thumb_widths = _const.THUMBNAIL_WIDTHS_SQUARE
        else:
            self._square_thumbs = False
            self._thumb_widths = _const.THUMBNAIL_WIDTHS_KEEP_ASPECT
        self.thumb_width = self.thumb_width

    @property
    def adult(self):
        """Whether images are for adults only"""
        return self._content_type != _const.CONTENT_TYPES['family']

    @adult.setter
    def adult(self, value):
        self._content_type = (_const.CONTENT_TYPES['adult'] if value
                              else _const.CONTENT_TYPES['family'])

    @property
    def comments_enabled(self):
        """
        Whether comments are enabled for this gallery

        This property can not be changed after create() was called.
        """
        return self._comments_enabled

    @comments_enabled.setter
    def comments_enabled(self, value):
        if self.created:
            raise RuntimeError('Gallery was already created')
        else:
            self._comments_enabled = bool(value)

    @property
    def url(self):
        """URL to gallery of thumbnails or None if create() was not called yet"""
        if self._gallery_token:
            return _const.GALLERY_URL_FORMAT.format(**self._gallery_token)
        else:
            return None

    @property
    def edit_url(self):
        """URL to manage gallery or None if create() was not called yet"""
        if self._gallery_token:
            return _const.EDIT_URL_FORMAT.format(**self._gallery_token)
        else:
            return None

    @property
    def created(self):
        """Whether this gallery was created remotely"""
        return bool(
            self._gallery_token and
            _const.CSRF_TOKEN_HEADER in self._client.headers,
        )

    async def create(self):
        """
        Create gallery remotely

        Properties like :attr:`title` cannot be changed after calling
        :meth:`create`.

        Raise ConnectionError if the creation request fails.

        Raise RuntimeError if this method is called twice or if the server
        responds in an unexpected way.
        """
        if self.created:
            raise RuntimeError('Gallery was already created')

        # Get CSRF token from entry page
        self._client.headers.pop(_const.CSRF_TOKEN_HEADER, None)
        text = await self._client.get(f'https://{_const.SERVICE_DOMAIN}/')

        # Find <meta content="..." name="csrf-token" />
        soup = bs4.BeautifulSoup(text, features="html.parser")
        csrf_token = ''
        for meta in soup.find_all('meta', {'name': 'csrf-token'}):
            csrf_token = meta.get('content')
            log.debug('Found CSRF token: %s', csrf_token)
        if not csrf_token:
            raise RuntimeError("Couldn't find CSRF token in HTML head")
        else:
            self._client.headers[_const.CSRF_TOKEN_HEADER] = csrf_token

        # Get token_id / token_secret + gallery_id / gallery_secret
        data = {
            'gallery': 'true',
            'gallery_title': self.title or '',
            'comments_enabled': '1' if self.comments_enabled else '0',
        }

        gallery_token = await self._client.post(
            url=_const.TOKEN_URL,
            data=data,
            json=True,
        )
        if not isinstance(gallery_token, dict):
            raise RuntimeError(f'Not a dict: {gallery_token!r}')
        else:
            self._gallery_token = gallery_token
            log.debug('Gallery token:\n%s', self._gallery_token)

    async def _submit_file(self, filepath, content_type, thumbnail_size):
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

        data = {
            'token_id': str(self._gallery_token['token_id']),
            'token_secret': str(self._gallery_token['token_secret']),
            'content_type': str(content_type),
            'thumbnail_size': str(thumbnail_size),
            'gallery_id': str(self._gallery_token.get('gallery_id', 'null')),
            'gallery_secret': str(self._gallery_token.get('gallery_secret', 'null')),
            'comments_enabled': '1' if self.comments_enabled else '0',
        }

        files = {
            'files[]': (
                os.path.basename(filepath),
                fileobj,
                mimetype,
            ),
        }

        try:
            response = await self._client.post(
                url=_const.PROCESS_URL,
                data=data,
                files=files,
                json=True,
            )
        except ConnectionError as e:
            return Submission(success=False, error=str(e), **submission)

        log.debug('POST response:\n%s', response)
        if 'files' not in response:
            raise RuntimeError(f"Unexpected response: Couldn't find 'files': {response}")
        elif not isinstance(response['files'], list):
            raise RuntimeError(f"Unexpected response: 'files' is not a list: {response}")
        elif not response['files']:
            raise RuntimeError(f"Unexpected response: 'files' is empty: {response}")

        info = response['files'][0]
        return Submission(
            success=True,
            filename=os.path.basename(filepath),
            filepath=filepath,
            image_url=info['original_url'],
            thumbnail_url=info['thumbnail_url'],
            web_url=info['url'],
            gallery_url=self.url,
            edit_url=self.edit_url,
        )

    async def add(self, *filepaths):
        """
        Upload images to this gallery, yield Submission objects

        filepaths: Iterable of image file paths

        Raise RuntimeError if create() was not called first
        """
        if not self.created:
            raise RuntimeError('create() must be called first')
        for filepath in filepaths:
            submission = await self._submit_file(filepath,
                                                 self._content_type,
                                                 self._thumbnail_width)
            yield submission

    def __repr__(self):
        return (f'{type(self).__name__}('
                f'title={repr(self.title)}, '
                f'thumb_width={repr(self.thumb_width)}, '
                f'square_thumbs={repr(self.square_thumbs)}, '
                f'adult={repr(self.adult)}, '
                f'comments_enabled={repr(self.comments_enabled)})')
