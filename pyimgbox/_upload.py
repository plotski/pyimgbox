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
    edit_url: URL to manage gallery or None

    All keys are also available as attributes for convenience.
    """

    def __init__(self, *, success, **kwargs):
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
        super().__init__(values)

    def __getattr__(self, name):
        value = self.get(name)
        if value is None:
            raise AttributeError(name)
        else:
            return value

    def __repr__(self):
        kwargs = ', '.join(f'{k}={v!r}'
                           for k,v in self.items()
                           if v is not None)
        return f'{type(self).__name__}({kwargs})'


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
        self._session = requests.Session()
        self._token = {}
        self.title = title
        self.square_thumbs = square_thumbs
        self.thumb_width = thumb_width
        self.adult = adult
        self.comments_enabled = comments_enabled

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
        if self._token:
            return _const.GALLERY_URL_FORMAT.format(**self._token)
        else:
            return None

    @property
    def edit_url(self):
        """URL to manage gallery or None if create() was not called yet"""
        if self._token:
            return _const.EDIT_URL_FORMAT.format(**self._token)
        else:
            return None

    @property
    def created(self):
        """Whether this gallery was created remotely"""
        return bool(_const.CSRF_TOKEN_HEADER in self._session.headers and self._token)

    def create(self):
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

        # Get token_id / token_secret + gallery_id / gallery_secret
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
            gallery_url=self.url,
            edit_url=self.edit_url,
        )

    def add(self, *filepaths, timeout=None):
        """
        Upload images to this gallery, yield Submission objects

        filepaths: Iterable of image file paths
        timeout: Number of seconds of no server response before giving up

        Raise RuntimeError if create() was not called first
        """
        if not self.created:
            raise RuntimeError('create() must be called first')
        for filepath in filepaths:
            yield self._submit_file(filepath,
                                    self._content_type,
                                    self._thumbnail_width,
                                    timeout=timeout)

    def __repr__(self):
        return (f'{type(self).__name__}('
                f'title={repr(self.title)}, '
                f'thumb_width={repr(self.thumb_width)}, '
                f'square_thumbs={repr(self.square_thumbs)}, '
                f'adult={repr(self.adult)}, '
                f'comments_enabled={repr(self._comments_enabled)})')
