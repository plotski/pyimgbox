import logging
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
    thumb_width: Thumbnail width in pixels; automatically snaps to closest
                 supported value
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
        await self.close()

    async def close(self):
        """Stop adding images to this gallery"""
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
        self._thumbnail_size = self._thumb_widths[self._thumb_width]

    @property
    def square_thumbs(self):
        """Whether thumbnails have the same height and width"""
        return self._square_thumbs

    @square_thumbs.setter
    def square_thumbs(self, value):
        if value:
            self._square_thumbs = True
            self._thumb_widths = _const.THUMBNAIL_SIZES_SQUARE
        else:
            self._square_thumbs = False
            self._thumb_widths = _const.THUMBNAIL_SIZES_KEEP_ASPECT
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
        """URL to gallery of thumbnails or None before create() was called"""
        if self._gallery_token:
            return _const.GALLERY_URL_FORMAT.format(**self._gallery_token)
        else:
            return None

    @property
    def edit_url(self):
        """URL to manage gallery or None before create() was called"""
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

        Some properties cannot be changed after calling this method. Other
        properties are only available after this method was called.

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
            log.debug('Gallery token: %s', self._gallery_token)

    def _prepare(self, *filepaths):
        """
        Return list of 3-tuples:
            (filepath,
             3-tuple: (filepath, fileobject, error) or None,
             error message or None)
        """
        files = []
        for filepath in filepaths:
            # Open file or get error message
            try:
                fileobj = open(filepath, 'rb')
            except OSError as e:
                files.append((filepath, None, e.strerror))
            else:
                # Check file size limit
                if os.path.getsize(filepath) > _const.MAX_FILE_SIZE:
                    files.append((
                        filepath,
                        None,
                        f'File is larger than {_const.MAX_FILE_SIZE} bytes'
                    ))

                # Store the tuple we need for the POST request
                else:
                    filetuple = (os.path.basename(filepath), fileobj)
                    files.append((filepath, filetuple, None))

        return files

    async def _upload_image(self, filepath, filetuple, error):
        """
        Upload image file

        filepath: Path to image file
        filetuple: (file name, file object)
        error: Error message or None

        Return Submission object.
        """
        # Report error before creating the gallery
        if error:
            assert filetuple is None, 'Arguments "filetuple" and "error" are mutually exclusive'
            return Submission(filepath=filepath, error=error)

        # Auto-create gallery
        if not self.created:
            try:
                await self.create()
            except ConnectionError as e:
                return Submission(filepath=filepath, error=str(e))

        # Build request
        data = {
            'token_id': str(self._gallery_token['token_id']),
            'token_secret': str(self._gallery_token['token_secret']),
            'gallery_id': str(self._gallery_token.get('gallery_id', 'null')),
            'gallery_secret': str(self._gallery_token.get('gallery_secret', 'null')),
            'content_type': str(self._content_type),
            'thumbnail_size': str(self._thumbnail_size),
            'comments_enabled': '1' if self.comments_enabled else '0',
        }
        files = {'files[]': filetuple}

        # Upload image
        try:
            response = await self._client.post(
                url=_const.PROCESS_URL,
                data=data,
                files=files,
                json=True,
            )
        except ConnectionError as e:
            return Submission(filepath=filepath, error=str(e))
        else:
            log.debug('POST response: %s', response)
            info = response['files'][0]
            return Submission(
                filepath=filepath,
                image_url=info['original_url'],
                thumbnail_url=info['thumbnail_url'],
                web_url=info['url'],
                gallery_url=self.url,
                edit_url=self.edit_url,
            )

    async def upload(self, filepath):
        """
        Upload image to this gallery

        filepath: Path to JPEG or PNG file

        Return Submission object.
        """
        filepath, filetuple, error = self._prepare(filepath)[0]
        return await self._upload_image(filepath, filetuple, error)

    async def add(self, filepaths):
        """
        Upload images to this gallery

        This is typically used in an `async for` loop:

        >>> async for submission in gallery.add(["foo.jpg", "bar.jpg"]):
        >>>     print(submission)

        filepaths: Iterable of paths to JPEG or PNG files

        Yield Submission objects asynchronously.
        """
        for filepath, filetuple, error in self._prepare(*filepaths):
            yield await self._upload_image(filepath, filetuple, error)

    def __repr__(self):
        return (
            f'{type(self).__name__}('
            f'title={repr(self.title)}, '
            f'thumb_width={repr(self.thumb_width)}, '
            f'square_thumbs={repr(self.square_thumbs)}, '
            f'adult={repr(self.adult)}, '
            f'comments_enabled={repr(self.comments_enabled)})'
        )
