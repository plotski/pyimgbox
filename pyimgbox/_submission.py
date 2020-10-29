import os


class Submission(dict):
    """
    Dictionary with the following keys:

    success: True or False
    error: Error message or None
    filename: File name or None
    filepath: File path or None
    image_url: URL to image or None
    thumbnail_url: URL to thumbnail or None
    web_url: URL to image's web page or None
    gallery_url: URL to web page of thumbnails or None
    edit_url: URL to manage gallery or None

    "success" is derived from "error".
    "filename" is derived from "filepath".

    All keys are also available as attributes for convenience.
    """

    def __init__(self, **kwargs):
        values = {
            'success': None,
            'error': None,
            'filepath': None,
            'filename': None,
            'image_url': None,
            'thumbnail_url': None,
            'web_url': None,
            'gallery_url': None,
            'edit_url': None,
        }
        for k in kwargs:
            assert k in values, f'Unknown key: {k!r}'

        if not kwargs.get('error'):
            for k in ('filepath', 'image_url', 'thumbnail_url',
                      'web_url', 'gallery_url', 'edit_url'):
                assert k in kwargs, f'Missing key: {k!r}'

        values.update(kwargs)

        if values.get('filepath'):
            values['filename'] = os.path.basename(values['filepath'])
        values['success'] = not bool(values.get('error'))

        super().__init__(values)

    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError:
            raise AttributeError(f'{type(self).__name__} object has no attribute {name!r}')

    def __repr__(self):
        kwargs = ', '.join(f'{k}={v!r}'
                           for k,v in self.items()
                           if v is not None)
        return f'{type(self).__name__}({kwargs})'
