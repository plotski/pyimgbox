import random
from unittest.mock import Mock, call, mock_open, patch

import pytest

from pyimgbox import _const, _upload


def test_Submission_needs_success_key():
    with pytest.raises(TypeError, match=r"required keyword-only argument: 'success'"):
        _upload.Submission(x='y')

def test_Submission_gets_unknown_key():
    with pytest.raises(AssertionError, match=r"^Unknown key: 'x'$"):
        _upload.Submission(success=False, x='y')

def test_Submission_gets_failure_and_no_error():
    with pytest.raises(AssertionError, match=r"^Missing key: 'error'$"):
        _upload.Submission(success=False, filename='foo')

def test_Submission_gets_conflicting_success_and_error():
    with pytest.raises(AssertionError, match=r"^Conflicting keys: 'error', 'success'$"):
        _upload.Submission(success=True, error='Huh?')

def test_Submission_gets_success_and_not_all_expected_keys():
    expected_keys = {'filename': 'Foo.jpg',
                     'filepath': 'path/to/Foo.jpg',
                     'image_url': 'https://foo.bar/asdf.jpg',
                     'thumbnail_url': 'https://foo.bar/asdf_t.jpg',
                     'web_url': 'https://foo.bar/asdf',
                     'gallery_url': 'https://foo.bar/fdsa',
                     'edit_url': 'https://foo.bar/fdsa/edit'}
    for k in expected_keys:
        with pytest.raises(AssertionError, match=rf"^Missing key: '{k}'$"):
            keys = expected_keys.copy()
            del keys[k]
            _upload.Submission(success=True, **keys)

def test_Submission_gets_valid_success_arguments():
    assert _upload.Submission(
        success=True,
        filename='Foo.jpg',
        filepath='path/to/Foo.jpg',
        image_url='https://foo.bar/asdf.jpg',
        thumbnail_url='https://foo.bar/asdf_t.jpg',
        web_url='https://foo.bar/asdf',
        gallery_url='https://foo.bar/fdsa',
        edit_url='https://foo.bar/fdsa/edit'
    ) == {'success': True,
          'filename': 'Foo.jpg',
          'filepath': 'path/to/Foo.jpg',
          'image_url': 'https://foo.bar/asdf.jpg',
          'thumbnail_url': 'https://foo.bar/asdf_t.jpg',
          'web_url': 'https://foo.bar/asdf',
          'gallery_url': 'https://foo.bar/fdsa',
          'edit_url': 'https://foo.bar/fdsa/edit'}

def test_Submission_gets_valid_error_arguments():
    assert _upload.Submission(
        success=False,
        error='Trouble is afoot!',
    ) == {'success': False,
          'error': 'Trouble is afoot!'}


def test_Gallery_title_property():
    assert _upload.Gallery(title='Foo, Bar, Baz').title == 'Foo, Bar, Baz'
    assert _upload.Gallery(title=(1, 2, 3)).title == '(1, 2, 3)'

def test_Gallery_comments_enabled_property():
    assert _upload.Gallery(comments_enabled=True).comments_enabled is True
    assert _upload.Gallery(comments_enabled=False).comments_enabled is False
    assert _upload.Gallery(comments_enabled=0).comments_enabled is False
    assert _upload.Gallery(comments_enabled='yes').comments_enabled is True

@patch('pyimgbox._utils.post_json')
@patch('pyimgbox._utils.get')
def test_Gallery_init_gets_invalid_html_from_landing_page(mock_get, mock_post_json):
    mock_get.return_value = '~~> This is not html. <-'
    gallery = _upload.Gallery()
    with pytest.raises(RuntimeError, match=r"Couldn't find CSRF token in HTML head"):
        gallery._init()
    assert _const.CSRF_TOKEN_HEADER not in gallery._session.headers
    assert gallery._token == {}
    assert gallery._initialized is False

@patch('pyimgbox._utils.post_json')
@patch('pyimgbox._utils.get')
def test_Gallery_init_ensures_token_is_dictionary(mock_get, mock_post_json):
    mock_get.return_value = ('<html><head>'
                             '<meta foo="bar" name="something" />'
                             '<meta content="THE-CSRF-TOKEN" name="csrf-token" />'
                             '<meta name="yo" />'
                             '</head></html>')
    mock_post_json.return_value = (1, 2, 3)
    gallery = _upload.Gallery(title='The Title', comments_enabled=True)
    with pytest.raises(RuntimeError, match=r'^Not a dict: \(1, 2, 3\)$'):
        gallery._init()
    assert gallery._token == {}
    assert gallery._initialized is False

@patch('pyimgbox._utils.post_json')
@patch('pyimgbox._utils.get')
def test_Gallery_init_sets_session_header_and_token(mock_get, mock_post_json):
    mock_get.return_value = ('<html><head>'
                             '<meta foo="bar" name="something" />'
                             '<meta content="THE-CSRF-TOKEN" name="csrf-token" />'
                             '<meta name="yo" />'
                             '</head></html>')
    mock_post_json.return_value = {'something': 'asdf', 'foo': 'bar'}

    gallery = _upload.Gallery(title='The Title', comments_enabled=True)
    assert gallery._initialized is False
    assert gallery._init() is None

    assert mock_get.call_args_list == [
        call(gallery._session, f'https://{_const.SERVICE_DOMAIN}/', timeout=30)]
    assert mock_post_json.call_args_list == [
        call(gallery._session, _const.TOKEN_URL, timeout=30,
             data=[('gallery', 'true'),
                   ('gallery_title', 'The Title'),
                   ('comments_enabled', '1')])
    ]

    assert gallery._session.headers[_const.CSRF_TOKEN_HEADER] == 'THE-CSRF-TOKEN'
    assert gallery._token == {'something': 'asdf', 'foo': 'bar'}
    assert gallery._initialized is True


@patch('pyimgbox._utils.get', Mock())
@patch('pyimgbox._utils.post_json')
def test_Gallery_submit_file_cannot_open_file(mock_post_json):
    gallery = _upload.Gallery()
    sub = gallery._submit_file('this/file/does/not/exist.jpg',
                               content_type=_const.CONTENT_TYPES['family'],
                               thumbnail_size=_const.THUMBNAIL_WIDTHS_SQUARE[200],
                               timeout=123)
    assert sub == {'success': False,
                   'error': 'No such file or directory',
                   'filename': 'exist.jpg',
                   'filepath': 'this/file/does/not/exist.jpg'}

@patch('pyimgbox._utils.get', Mock())
@patch('builtins.open', mock_open(read_data='foo'))
@patch('mimetypes.guess_type')
@patch('pyimgbox._utils.post_json')
def test_Gallery_submit_file_gets_file_with_unknown_mimetype(mock_post_json, mock_guess_type):
    mock_guess_type.return_value = (None, None)
    gallery = _upload.Gallery()
    sub = gallery._submit_file('path/to/file.jpg',
                               content_type=_const.CONTENT_TYPES['family'],
                               thumbnail_size=_const.THUMBNAIL_WIDTHS_SQUARE[200],
                               timeout=123)
    assert sub == {'success': False,
                   'error': 'Unknown mime type',
                   'filename': 'file.jpg',
                   'filepath': 'path/to/file.jpg'}

@patch('pyimgbox._utils.get', Mock())
@patch('builtins.open', mock_open(read_data='foo'))
@patch('mimetypes.guess_type')
@patch('pyimgbox._utils.post_json')
def test_Gallery_submit_file_gets_file_with_unsupported_mimetype(mock_post_json, mock_guess_type):
    mock_guess_type.return_value = ('text/plain', None)
    gallery = _upload.Gallery()
    sub = gallery._submit_file('path/to/file.txt',
                               content_type=_const.CONTENT_TYPES['family'],
                               thumbnail_size=_const.THUMBNAIL_WIDTHS_SQUARE[200],
                               timeout=123)
    assert sub == {'success': False,
                   'error': 'Unsupported file type: text/plain',
                   'filename': 'file.txt',
                   'filepath': 'path/to/file.txt'}

@patch('pyimgbox._utils.get', Mock())
@patch('builtins.open', mock_open(read_data='foo'))
@patch('pyimgbox._utils.post_json')
def test_Gallery_submit_file_raises_OSError(mock_post_json):
    gallery = _upload.Gallery()
    mock_token = {'token_id': '123', 'token_secret': '456',
                  'gallery_id': 'abc', 'gallery_secret': 'def'}
    gallery._token = mock_token
    mock_post_json.side_effect = ConnectionError('Network is unreachable')
    sub = gallery._submit_file('path/to/file.jpg',
                               content_type=_const.CONTENT_TYPES['family'],
                               thumbnail_size=_const.THUMBNAIL_WIDTHS_SQUARE[200],
                               timeout=123)
    assert sub == {'success': False,
                   'error': 'Network is unreachable',
                   'filename': 'file.jpg',
                   'filepath': 'path/to/file.jpg'}
    assert mock_post_json.call_args_list == [
        call(
            gallery._session, _const.PROCESS_URL,
            data=[
                ('token_id', mock_token['token_id']),
                ('token_secret', mock_token['token_secret']),
                ('content_type', _const.CONTENT_TYPES['family']),
                ('thumbnail_size', _const.THUMBNAIL_WIDTHS_SQUARE[200]),
                ('gallery_id', mock_token['gallery_id']),
                ('gallery_secret', mock_token['gallery_secret']),
                ('comments_enabled', '0'),
            ],
            files=[('files[]', ('file.jpg',
                                open('path/to/file.jpg'),
                                'image/jpeg'))],
            timeout=123,
        )
    ]

@patch('pyimgbox._utils.get', Mock())
@patch('builtins.open', mock_open(read_data='foo'))
@patch('pyimgbox._utils.post_json')
def test_Gallery_submit_file_raises_ValueError(mock_post_json):
    gallery = _upload.Gallery()
    mock_token = {'token_id': '123', 'token_secret': '456',
                  'gallery_id': 'abc', 'gallery_secret': 'def'}
    gallery._token = mock_token
    mock_post_json.side_effect = ValueError('Error while parsing JSON')
    sub = gallery._submit_file('path/to/file.jpg',
                               content_type=_const.CONTENT_TYPES['adult'],
                               thumbnail_size=_const.THUMBNAIL_WIDTHS_SQUARE[300],
                               timeout=12)
    assert sub == {'success': False,
                   'error': 'Error while parsing JSON',
                   'filename': 'file.jpg',
                   'filepath': 'path/to/file.jpg'}
    assert mock_post_json.call_args_list == [
        call(
            gallery._session, _const.PROCESS_URL,
            data=[
                ('token_id', mock_token['token_id']),
                ('token_secret', mock_token['token_secret']),
                ('content_type', _const.CONTENT_TYPES['adult']),
                ('thumbnail_size', _const.THUMBNAIL_WIDTHS_SQUARE[300]),
                ('gallery_id', mock_token['gallery_id']),
                ('gallery_secret', mock_token['gallery_secret']),
                ('comments_enabled', '0'),
            ],
            files=[('files[]', ('file.jpg',
                                open('path/to/file.jpg'),
                                'image/jpeg'))],
            timeout=12,
        )
    ]

@patch('pyimgbox._utils.get', Mock())
@patch('builtins.open', mock_open(read_data='foo'))
@patch('pyimgbox._utils.post_json')
def test_Gallery_submit_file_gets_json_response_without_files_field(mock_post_json):
    gallery = _upload.Gallery()
    mock_token = {'token_id': '123', 'token_secret': '456',
                  'gallery_id': 'abc', 'gallery_secret': 'def'}
    gallery._token = mock_token
    mock_post_json.return_value = {'not files': 'asdf'}
    with pytest.raises(RuntimeError) as cm:
        gallery._submit_file('path/to/file.jpg',
                             content_type=_const.CONTENT_TYPES['adult'],
                             thumbnail_size=_const.THUMBNAIL_WIDTHS_SQUARE[300],
                             timeout=12)
    assert str(cm.value) == "Unexpected response: Couldn't find 'files': {'not files': 'asdf'}"

@patch('pyimgbox._utils.get', Mock())
@patch('builtins.open', mock_open(read_data='foo'))
@patch('pyimgbox._utils.post_json')
def test_Gallery_submit_file_gets_json_response_with_nonlist_files_field(mock_post_json):
    gallery = _upload.Gallery()
    mock_token = {'token_id': '123', 'token_secret': '456',
                  'gallery_id': 'abc', 'gallery_secret': 'def'}
    gallery._token = mock_token
    mock_post_json.return_value = {'files': 'asdf'}
    with pytest.raises(RuntimeError) as cm:
        gallery._submit_file('path/to/file.jpg',
                             content_type=_const.CONTENT_TYPES['adult'],
                             thumbnail_size=_const.THUMBNAIL_WIDTHS_SQUARE[300],
                             timeout=12)
    assert str(cm.value) == "Unexpected response: 'files' is not a list: {'files': 'asdf'}"

@patch('pyimgbox._utils.get', Mock())
@patch('builtins.open', mock_open(read_data='foo'))
@patch('pyimgbox._utils.post_json')
def test_Gallery_submit_file_gets_json_response_with_files_field(mock_post_json):
    gallery = _upload.Gallery()
    mock_token = {'token_id': '123', 'token_secret': '456',
                  'gallery_id': 'abc', 'gallery_secret': 'def'}
    gallery._token = mock_token
    mock_post_json.return_value = {'files': []}
    with pytest.raises(RuntimeError) as cm:
        gallery._submit_file('path/to/file.jpg',
                             content_type=_const.CONTENT_TYPES['adult'],
                             thumbnail_size=_const.THUMBNAIL_WIDTHS_SQUARE[300],
                             timeout=12)
    assert str(cm.value) == "Unexpected response: 'files' is empty: {'files': []}"

@patch('pyimgbox._utils.get', Mock())
@patch('builtins.open', mock_open(read_data='foo'))
@patch('pyimgbox._utils.post_json')
def test_Gallery_submit_file_succeeds(mock_post_json):
    gallery = _upload.Gallery()
    mock_token = {'token_id': '123', 'token_secret': '456',
                  'gallery_id': 'abc', 'gallery_secret': 'def'}
    gallery._token = mock_token
    mock_post_json.return_value = {'files': [{'original_url': 'https://foo.example.org/asdf.jpg',
                                              'thumbnail_url': 'https://foo.example.org/asdf_t.jpg',
                                              'url': 'https://foo.example.org/asdf'}]}
    sub = gallery._submit_file('path/to/file.jpg',
                               content_type=_const.CONTENT_TYPES['adult'],
                               thumbnail_size=_const.THUMBNAIL_WIDTHS_SQUARE[300],
                               timeout=12)
    assert sub == _upload.Submission(
        success=True,
        filename='file.jpg',
        filepath='path/to/file.jpg',
        image_url='https://foo.example.org/asdf.jpg',
        thumbnail_url='https://foo.example.org/asdf_t.jpg',
        web_url='https://foo.example.org/asdf',
        gallery_url=_const.GALLERY_URL_FORMAT.format(**mock_token),
        edit_url=_const.EDIT_URL_FORMAT.format(**mock_token),
    )


@patch('pyimgbox._utils.get', Mock())
@patch('pyimgbox._utils.post_json', Mock())
def test_Gallery_submit_does_not_inititialize_without_filepaths():
    gallery = _upload.Gallery()
    mock_init = Mock()
    mock_submit_file = Mock()
    with patch.multiple(gallery, _init=mock_init, _submit_file=mock_submit_file):
        assert mock_init.call_args_list == []
        assert tuple(gallery.submit()) == ()
        assert mock_init.call_args_list == []
        assert mock_submit_file.call_args_list == []

@patch('pyimgbox._utils.get', Mock())
@patch('pyimgbox._utils.post_json', Mock())
def test_Gallery_submit_calls_inititializes_automatically_but_only_once():
    filepaths = ('foo.jpg', 'bar.jpg')
    gallery = _upload.Gallery()
    mock_init = Mock()
    mock_submit_file = Mock()
    with patch.multiple(gallery, _init=mock_init, _submit_file=mock_submit_file):
        assert mock_init.call_args_list == []
        for sub in gallery.submit(*filepaths):
            assert mock_init.call_args_list == [call()]
        assert mock_submit_file.call_args_list == [call('foo.jpg',
                                                        _const.CONTENT_TYPES['family'],
                                                        _const.THUMBNAIL_WIDTHS_KEEP_ASPECT[100],
                                                        timeout=None),
                                                   call('bar.jpg',
                                                        _const.CONTENT_TYPES['family'],
                                                        _const.THUMBNAIL_WIDTHS_KEEP_ASPECT[100],
                                                        timeout=None)]

@patch('pyimgbox._utils.get', Mock())
@patch('pyimgbox._utils.post_json', Mock())
def test_Gallery_submit_catches_OSError_from_init():
    filepaths = ('foo.jpg', 'bar.jpg')
    gallery = _upload.Gallery()
    mock_init = Mock(side_effect=ConnectionError('Argh'))
    mock_submit_file = Mock()
    with patch.multiple(gallery, _init=mock_init, _submit_file=mock_submit_file):
        for sub in gallery.submit(*filepaths):
            assert sub == _upload.Submission(success=False, error='Argh')
        assert mock_submit_file.call_args_list == []

@patch('pyimgbox._utils.get', Mock())
@patch('pyimgbox._utils.post_json', Mock())
def test_Gallery_submit_catches_ValueError_from_init():
    filepaths = ('foo.jpg', 'bar.jpg')
    gallery = _upload.Gallery()
    mock_init = Mock(side_effect=ValueError('Argh'))
    mock_submit_file = Mock()
    with patch.multiple(gallery, _init=mock_init, _submit_file=mock_submit_file):
        for sub in gallery.submit(*filepaths):
            assert sub == _upload.Submission(success=False, error='Argh')
        assert mock_submit_file.call_args_list == []

@patch('pyimgbox._utils.get', Mock())
@patch('pyimgbox._utils.post_json', Mock())
def test_Gallery_submit_handles_nsfw_argument():
    filepaths = ('path/to/foo.jpg',)
    gallery = _upload.Gallery()
    mock_init = Mock()
    mock_submit_file = Mock()
    with patch.multiple(gallery, _init=mock_init, _submit_file=mock_submit_file):
        for sub in gallery.submit(*filepaths, nsfw=False):
            pass
        assert mock_submit_file.call_args_list == [call('path/to/foo.jpg',
                                                        _const.CONTENT_TYPES['family'],
                                                        _const.THUMBNAIL_WIDTHS_KEEP_ASPECT[100],
                                                        timeout=None)]
        mock_submit_file.reset_mock()
        for sub in gallery.submit(*filepaths, nsfw=True):
            pass
        assert mock_submit_file.call_args_list == [call('path/to/foo.jpg',
                                                        _const.CONTENT_TYPES['adult'],
                                                        _const.THUMBNAIL_WIDTHS_KEEP_ASPECT[100],
                                                        timeout=None)]

@patch('pyimgbox._utils.get', Mock())
@patch('pyimgbox._utils.post_json', Mock())
def test_Gallery_submit_handles_thumb_width_and_square_thumbs_arguments():
    filepaths = ('path/to/foo.jpg',)
    gallery = _upload.Gallery()
    mock_init = Mock()
    mock_submit_file = Mock()
    with patch.multiple(gallery, _init=mock_init, _submit_file=mock_submit_file):
        for (width, code) in _const.THUMBNAIL_WIDTHS_SQUARE.items():
            # Provide existing thumb_width
            for sub in gallery.submit(*filepaths, thumb_width=width, square_thumbs=True):
                pass
            assert mock_submit_file.call_args_list == [call('path/to/foo.jpg',
                                                            _const.CONTENT_TYPES['family'],
                                                            code,
                                                            timeout=None)]
            mock_submit_file.reset_mock()
            # Provide any thumb_width and automatically pick closest existing
            for sub in gallery.submit(*filepaths,
                                      thumb_width=width+random.randint(-10, 10),
                                      square_thumbs=True):
                pass
            assert mock_submit_file.call_args_list == [call('path/to/foo.jpg',
                                                            _const.CONTENT_TYPES['family'],
                                                            code,
                                                            timeout=None)]
            mock_submit_file.reset_mock()

        for (width, code) in _const.THUMBNAIL_WIDTHS_KEEP_ASPECT.items():
            # Provide existing thumb_width
            for sub in gallery.submit(*filepaths, thumb_width=width, square_thumbs=False):
                pass
            assert mock_submit_file.call_args_list == [call('path/to/foo.jpg',
                                                            _const.CONTENT_TYPES['family'],
                                                            code,
                                                            timeout=None)]
            mock_submit_file.reset_mock()
            # Provide any thumb_width and automatically pick closest existing
            for sub in gallery.submit(*filepaths,
                                      thumb_width=width+random.randint(-10, 10),
                                      square_thumbs=False):
                pass
            assert mock_submit_file.call_args_list == [call('path/to/foo.jpg',
                                                            _const.CONTENT_TYPES['family'],
                                                            code,
                                                            timeout=None)]
            mock_submit_file.reset_mock()

@patch('pyimgbox._utils.get', Mock())
@patch('pyimgbox._utils.post_json', Mock())
def test_Gallery_submit_handles_timeout_argument():
    filepaths = ('path/to/foo.jpg',)
    gallery = _upload.Gallery()
    mock_init = Mock()
    mock_submit_file = Mock()
    with patch.multiple(gallery, _init=mock_init, _submit_file=mock_submit_file):
        for sub in gallery.submit(*filepaths, timeout=999):
            pass
        assert mock_submit_file.call_args_list == [call('path/to/foo.jpg',
                                                        _const.CONTENT_TYPES['family'],
                                                        _const.THUMBNAIL_WIDTHS_KEEP_ASPECT[100],
                                                        timeout=999)]
