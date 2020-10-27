import os
from unittest.mock import Mock, call, patch

import pytest

from pyimgbox import Gallery, Submission, _const
from pyimgbox._http import HTTPClient


# Python 3.6 doesn't have AsyncMock
class AsyncMock(Mock):
    def __call__(self, *args, **kwargs):
        async def coro(_sup=super()):
            return _sup.__call__(*args, **kwargs)
        return coro()


@pytest.fixture
async def client(mocker):
    mocker.patch('pyimgbox._http.HTTPClient.get', AsyncMock())
    mocker.patch('pyimgbox._http.HTTPClient.post', AsyncMock())
    client = HTTPClient()
    yield client
    await client.close()


def test_Gallery_property_title():
    assert Gallery().title is None
    g = Gallery(title='Foo, Bar, Baz')
    assert g.title == 'Foo, Bar, Baz'
    g.title = (1, 2, 3)
    assert g.title == '(1, 2, 3)'
    g.title = None
    assert g.title is None
    g._gallery_token = {'something': 'truthy'}
    g._client.headers[_const.CSRF_TOKEN_HEADER] = 'mock token'
    with pytest.raises(RuntimeError, match=r'^Gallery was already created$'):
        g.title = 'Foo'


def test_Gallery_properties_thumb_width_and_square_thumbs():
    assert isinstance(Gallery().thumb_width, int)
    assert isinstance(Gallery().square_thumbs, bool)
    g = Gallery(thumb_width=200, square_thumbs=False)
    assert g.thumb_width == 200
    assert g.square_thumbs is False
    assert g._thumbnail_width == _const.THUMBNAIL_WIDTHS_KEEP_ASPECT[200]
    g.square_thumbs = True
    assert g.thumb_width == 200
    assert g.square_thumbs is True
    assert g._thumbnail_width == _const.THUMBNAIL_WIDTHS_SQUARE[200]
    g.thumb_width = 321
    assert g.thumb_width == 300
    assert g.square_thumbs is True
    assert g._thumbnail_width == _const.THUMBNAIL_WIDTHS_SQUARE[300]
    g.square_thumbs = 0
    assert g.thumb_width == 300
    assert g.square_thumbs is False
    assert g._thumbnail_width == _const.THUMBNAIL_WIDTHS_KEEP_ASPECT[300]


def test_Gallery_property_adult():
    assert isinstance(Gallery().adult, bool)
    g = Gallery(adult=True)
    assert g.adult is True
    g.adult = False
    assert g.adult is False
    g.adult = 1
    assert g.adult is True


def test_Gallery_property_comments_enabled():
    assert isinstance(Gallery().comments_enabled, bool)
    g = Gallery(comments_enabled=True)
    assert g.comments_enabled is True
    g.comments_enabled = False
    assert g.comments_enabled is False
    g.comments_enabled = 1
    assert g.comments_enabled is True


@pytest.mark.asyncio
async def test_Gallery_create_gets_invalid_html_from_landing_page(client):
    client.get.return_value = '~~> This is not html. <-'
    async with Gallery() as g:
        with pytest.raises(RuntimeError, match=r"Couldn't find CSRF token in HTML head"):
            await g.create()
    assert _const.CSRF_TOKEN_HEADER not in g._client.headers
    assert g._gallery_token == {}
    assert g.created is False

@pytest.mark.asyncio
async def test_Gallery_create_ensures_token_is_dictionary(client):
    client.get.return_value = ('<html><head>'
                               '<meta foo="bar" name="something" />'
                               '<meta content="THE-CSRF-TOKEN" name="csrf-token" />'
                               '<meta name="yo" />'
                               '</head></html>')
    client.post.return_value = [1, 2, 3]
    g = Gallery()
    with pytest.raises(RuntimeError, match=r'^Not a dict: \[1, 2, 3\]$'):
        await g.create()
    assert _const.CSRF_TOKEN_HEADER in g._client.headers
    assert g._gallery_token == {}
    assert g.created is False

@pytest.mark.asyncio
async def test_Gallery_create_sets_session_header_and_token(client):
    client.get.return_value = ('<html><head>'
                               '<meta foo="bar" name="something" />'
                               '<meta content="THE-CSRF-TOKEN" name="csrf-token" />'
                               '<meta name="yo" />'
                               '</head></html>')
    client.post.return_value = {'something': 'asdf', 'foo': 'bar'}
    g = Gallery(title='The Title', comments_enabled=True)
    assert g.created is False
    await g.create()
    assert client.get.call_args_list == [
        call(f'https://{_const.SERVICE_DOMAIN}/'),
    ]
    assert client.post.call_args_list == [
        call(
            url=_const.TOKEN_URL,
            data={
                'gallery': 'true',
                'gallery_title': 'The Title',
                'comments_enabled': '1',
            },
            json=True,
        ),
    ]
    assert g._client.headers == {_const.CSRF_TOKEN_HEADER: 'THE-CSRF-TOKEN'}
    assert g._gallery_token == {'something': 'asdf', 'foo': 'bar'}
    assert g.created is True

    with pytest.raises(RuntimeError, match=r'^Gallery was already created$'):
        await g.create()


@pytest.mark.asyncio
async def test_Gallery_submit_file_before_create_was_called(client):
    g = Gallery()
    with pytest.raises(RuntimeError, match=r'^create\(\) must be called first$'):
        await g._submit_file('this/file/does/not/exist.jpg')

@pytest.mark.asyncio
async def test_Gallery_submit_file_cannot_open_file(client):
    g = Gallery()
    g._client.headers[_const.CSRF_TOKEN_HEADER] = 'csrf token'
    g._gallery_token = {'token_id': '123', 'token_secret': '456',
                        'gallery_id': 'abc', 'gallery_secret': 'def'}
    s = await g._submit_file('this/file/does/not/exist.jpg')
    assert s == {
        'success': False,
        'error': 'No such file or directory',
        'filename': 'exist.jpg',
        'filepath': 'this/file/does/not/exist.jpg',
        'image_url': None,
        'thumbnail_url': None,
        'web_url': None,
        'gallery_url': None,
        'edit_url': None,
    }

@pytest.mark.asyncio
async def test_Gallery_submit_file_gets_too_large_file(client, tmp_path):
    filepath = tmp_path / 'foo.png'
    # Create sparse file
    f = open(filepath, 'wb')
    f.truncate(_const.MAX_FILE_SIZE + 1)
    f.close()
    g = Gallery()
    g._client.headers[_const.CSRF_TOKEN_HEADER] = 'csrf token'
    g._gallery_token = {'token_id': '123', 'token_secret': '456',
                        'gallery_id': 'abc', 'gallery_secret': 'def'}
    s = await g._submit_file(filepath)
    assert s == {
        'success': False,
        'error': f'File is larger than {_const.MAX_FILE_SIZE} bytes',
        'filename': 'foo.png',
        'filepath': filepath,
        'image_url': None,
        'thumbnail_url': None,
        'web_url': None,
        'gallery_url': None,
        'edit_url': None,
    }

@pytest.mark.asyncio
async def test_Gallery_submit_file_gets_file_with_unknown_mimetype(client, mocker):
    mocker.patch('builtins.open', mocker.mock_open(read_data='foo'))
    mocker.patch('mimetypes.guess_type', return_value=(None, None))
    mocker.patch('os.path.getsize', return_value=1048567)
    g = Gallery()
    g._client.headers[_const.CSRF_TOKEN_HEADER] = 'csrf token'
    g._gallery_token = {'token_id': '123', 'token_secret': '456',
                        'gallery_id': 'abc', 'gallery_secret': 'def'}
    s = await g._submit_file('path/to/file.jpg')
    assert s == {
        'success': False,
        'error': 'Unknown mime type',
        'filename': 'file.jpg',
        'filepath': 'path/to/file.jpg',
        'image_url': None,
        'thumbnail_url': None,
        'web_url': None,
        'gallery_url': None,
        'edit_url': None,
    }

@pytest.mark.asyncio
async def test_Gallery_submit_file_gets_file_with_unsupported_mimetype(client, mocker):
    mocker.patch('builtins.open', mocker.mock_open(read_data='foo'))
    mocker.patch('mimetypes.guess_type', return_value=('text/plain', None))
    mocker.patch('os.path.getsize', return_value=1048567)
    g = Gallery()
    g._client.headers[_const.CSRF_TOKEN_HEADER] = 'csrf token'
    g._gallery_token = {'token_id': '123', 'token_secret': '456',
                        'gallery_id': 'abc', 'gallery_secret': 'def'}
    s = await g._submit_file('path/to/file.txt')
    assert s == {
        'success': False,
        'error': 'Unsupported file type: text/plain',
        'filename': 'file.txt',
        'filepath': 'path/to/file.txt',
        'image_url': None,
        'thumbnail_url': None,
        'web_url': None,
        'gallery_url': None,
        'edit_url': None,
    }

@pytest.mark.asyncio
async def test_Gallery_submit_file_catches_ConnectionError_from_client(client, mocker):
    mocker.patch('builtins.open', mocker.mock_open(read_data='foo'))
    mocker.patch('mimetypes.guess_type', return_value=('image/jpeg', None))
    mocker.patch('os.path.getsize', return_value=1048567)
    g = Gallery()
    g._client.headers[_const.CSRF_TOKEN_HEADER] = 'csrf token'
    g._gallery_token = {'token_id': '123', 'token_secret': '456',
                        'gallery_id': 'abc', 'gallery_secret': 'def'}
    client.post.side_effect = ConnectionError('Network is unreachable')
    s = await g._submit_file('path/to/file.jpg')
    assert s == {
        'success': False,
        'error': 'Network is unreachable',
        'filename': 'file.jpg',
        'filepath': 'path/to/file.jpg',
        'image_url': None,
        'thumbnail_url': None,
        'web_url': None,
        'gallery_url': None,
        'edit_url': None,
    }
    assert client.post.call_args_list == [
        call(
            url=_const.PROCESS_URL,
            data={
                'token_id': g._gallery_token['token_id'],
                'token_secret': g._gallery_token['token_secret'],
                'content_type': g._content_type,
                'thumbnail_size': g._thumbnail_width,
                'gallery_id': g._gallery_token['gallery_id'],
                'gallery_secret': g._gallery_token['gallery_secret'],
                'comments_enabled': '0',
            },
            files={
                'files[]': ('file.jpg', open('path/to/file.jpg'), 'image/jpeg'),
            },
            json=True,
        ),
    ]

@pytest.mark.asyncio
async def test_Gallery_submit_file_gets_json_response_without_files_field(client, mocker):
    mocker.patch('builtins.open', mocker.mock_open(read_data='foo'))
    mocker.patch('mimetypes.guess_type', return_value=('image/jpeg', None))
    mocker.patch('os.path.getsize', return_value=1048567)
    g = Gallery()
    g._client.headers[_const.CSRF_TOKEN_HEADER] = 'csrf token'
    g._gallery_token = {'token_id': '123', 'token_secret': '456',
                        'gallery_id': 'abc', 'gallery_secret': 'def'}
    client.post.return_value = {'not files': 'asdf'}
    with pytest.raises(RuntimeError) as cm:
        await g._submit_file('path/to/file.jpg')
    assert str(cm.value) == "Unexpected response: Couldn't find 'files': {'not files': 'asdf'}"

@pytest.mark.asyncio
async def test_Gallery_submit_file_gets_json_response_with_nonlist_files_field(client, mocker):
    mocker.patch('builtins.open', mocker.mock_open(read_data='foo'))
    mocker.patch('mimetypes.guess_type', return_value=('image/jpeg', None))
    mocker.patch('os.path.getsize', return_value=1048567)
    g = Gallery()
    g._client.headers[_const.CSRF_TOKEN_HEADER] = 'csrf token'
    g._gallery_token = {'token_id': '123', 'token_secret': '456',
                        'gallery_id': 'abc', 'gallery_secret': 'def'}
    client.post.return_value = {'files': 'asdf'}
    with pytest.raises(RuntimeError) as cm:
        await g._submit_file('path/to/file.jpg')
    assert str(cm.value) == "Unexpected response: 'files' is not a list: {'files': 'asdf'}"

@pytest.mark.asyncio
async def test_Gallery_submit_file_gets_json_response_with_files_field(client, mocker):
    mocker.patch('builtins.open', mocker.mock_open(read_data='foo'))
    mocker.patch('mimetypes.guess_type', return_value=('image/jpeg', None))
    mocker.patch('os.path.getsize', return_value=1048567)
    g = Gallery()
    g._client.headers[_const.CSRF_TOKEN_HEADER] = 'csrf token'
    g._gallery_token = {'token_id': '123', 'token_secret': '456',
                        'gallery_id': 'abc', 'gallery_secret': 'def'}
    client.post.return_value = {'files': []}
    with pytest.raises(RuntimeError) as cm:
        await g._submit_file('path/to/file.jpg')
    assert str(cm.value) == "Unexpected response: 'files' is empty: {'files': []}"

@pytest.mark.asyncio
async def test_Gallery_submit_file_succeeds(client, mocker):
    mocker.patch('builtins.open', mocker.mock_open(read_data='foo'))
    mocker.patch('mimetypes.guess_type', return_value=('image/jpeg', None))
    mocker.patch('os.path.getsize', return_value=1048567)
    g = Gallery()
    g._client.headers[_const.CSRF_TOKEN_HEADER] = 'csrf token'
    g._gallery_token = {'token_id': '123', 'token_secret': '456',
                        'gallery_id': 'abc', 'gallery_secret': 'def'}
    client.post.return_value = {
        'files': [{'original_url': 'https://foo.example.org/asdf.jpg',
                   'thumbnail_url': 'https://foo.example.org/asdf_t.jpg',
                   'url': 'https://foo.example.org/asdf'}],
    }
    s = await g._submit_file('path/to/file.jpg')
    assert s == Submission(
        success=True,
        filename='file.jpg',
        filepath='path/to/file.jpg',
        image_url='https://foo.example.org/asdf.jpg',
        thumbnail_url='https://foo.example.org/asdf_t.jpg',
        web_url='https://foo.example.org/asdf',
        gallery_url=_const.GALLERY_URL_FORMAT.format(**g._gallery_token),
        edit_url=_const.EDIT_URL_FORMAT.format(**g._gallery_token),
    )


@pytest.mark.asyncio
async def test_Gallery_upload(client, mocker):
    g = Gallery()
    with patch.object(g, '_submit_file', AsyncMock()):
        submission = await g.upload('path/to/foo.jpg')
        assert g._submit_file.call_args_list == [call('path/to/foo.jpg')]
        assert submission is g._submit_file.return_value


@pytest.mark.asyncio
async def test_Gallery_add(client, mocker):
    filepaths = ('path/to/foo.jpg', 'path/to/bar.jpg')
    g = Gallery()
    with patch.object(g, '_submit_file', AsyncMock()):
        submissions_expected = [
            f'{filepath} submission' for filepath in filepaths
        ]
        submissions_seen = []
        g._submit_file.side_effect = submissions_expected
        async for submission in g.add(*filepaths):
            submissions_seen.append(submission)
        assert submissions_seen == submissions_expected
        assert g._submit_file.call_args_list == [
            call(filepath) for filepath in filepaths
        ]
