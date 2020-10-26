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
