import os
import re
import sys
from unittest.mock import Mock, call, patch

import pytest
import pytest_asyncio

from pyimgbox import Gallery, Submission, _const
from pyimgbox._http import HTTPClient


# Python 3.6 doesn't have AsyncMock
class AsyncMock(Mock):
    def __call__(self, *args, **kwargs):
        async def coro(_sup=super()):
            return _sup.__call__(*args, **kwargs)
        return coro()


@pytest_asyncio.fixture
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
    assert g._thumbnail_size == _const.THUMBNAIL_SIZES_KEEP_ASPECT[200]
    g.square_thumbs = True
    assert g.thumb_width == 200
    assert g.square_thumbs is True
    assert g._thumbnail_size == _const.THUMBNAIL_SIZES_SQUARE[200]
    g.thumb_width = 321
    assert g.thumb_width == 300
    assert g.square_thumbs is True
    assert g._thumbnail_size == _const.THUMBNAIL_SIZES_SQUARE[300]
    g.square_thumbs = 0
    assert g.thumb_width == 300
    assert g.square_thumbs is False
    assert g._thumbnail_size == _const.THUMBNAIL_SIZES_KEEP_ASPECT[300]
    with pytest.raises(ValueError, match=r"^Not a number: 'foo'$"):
        g.thumb_width = 'foo'


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
    g._gallery_token = 'mock token'
    g._client.headers[_const.CSRF_TOKEN_HEADER] = 'mock csrf'
    with pytest.raises(RuntimeError, match=r'^Gallery was already created$'):
        g.comments_enabled = False


def test_Gallery_property_url():
    g = Gallery()
    assert g.url is None
    g._gallery_token = {'gallery_id': 'mock token'}
    g._client.headers[_const.CSRF_TOKEN_HEADER] = 'mock csrf'
    assert g.url == _const.GALLERY_URL_FORMAT.format(**g._gallery_token)


def test_Gallery_property_edit_url():
    g = Gallery()
    assert g.edit_url is None
    g._gallery_token = {'token_id': 'mock token', 'token_secret': 'mock secret'}
    g._client.headers[_const.CSRF_TOKEN_HEADER] = 'mock csrf'
    assert g.edit_url == _const.EDIT_URL_FORMAT.format(**g._gallery_token)


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


def test_prepare_fails_to_open_file(mocker):
    filepaths = [
        'path/to/file0.jpg',
        'path/file1.jpg',
        'path/where/file2.jpg',
    ]
    mocker.patch('builtins.open', Mock(
        side_effect=[
            'fileobj0',
            OSError('mock errno', 'No such file'),
            'fileobj2',
        ],
    ))
    mocker.patch('os.path.getsize', return_value=1048576)
    g = Gallery()
    submissions = g._prepare(*filepaths)
    assert submissions == [
        (filepaths[0], (os.path.basename(filepaths[0]), 'fileobj0'), None),
        (filepaths[1], None, 'No such file'),
        (filepaths[2], (os.path.basename(filepaths[2]), 'fileobj2'), None),
    ]

def test_prepare_finds_large_file(mocker):
    filepaths = [
        'path/to/file0.jpg',
        'path/file1.jpg',
        'path/where/file2.jpg',
    ]
    mocker.patch('builtins.open', Mock(side_effect=['fileobj0', 'fileobj1', 'fileobj2']))
    mocker.patch('os.path.getsize', side_effect=[1048576, _const.MAX_FILE_SIZE + 1, 1048576])
    g = Gallery()
    submissions = g._prepare(*filepaths)
    assert submissions == [
        (filepaths[0], (os.path.basename(filepaths[0]), 'fileobj0'), None),
        (filepaths[1], None, f'File is larger than {_const.MAX_FILE_SIZE} bytes'),
        (filepaths[2], (os.path.basename(filepaths[2]), 'fileobj2'), None),
    ]


@pytest.mark.asyncio
async def test_upload_image_gets_error_and_filetuple_arguments(client):
    g = Gallery()
    with patch.object(g, 'create'):
        with pytest.raises(AssertionError, match=r'Arguments "filetuple" and "error" are mutually exclusive'):
            await g._upload_image('foo.jpg', 'fileobj', 'Something went wrong')
        assert g.create.call_args_list == []

@pytest.mark.asyncio
async def test_upload_image_gets_error_via_argument(client):
    g = Gallery()
    with patch.object(g, 'create'):
        sub = await g._upload_image('foo.jpg', None, 'Something went wrong')
        assert sub == Submission(filepath='foo.jpg', error='Something went wrong')
        assert g.create.call_args_list == []

@pytest.mark.asyncio
async def test_upload_image_calls_create_if_necessary(client):
    g = Gallery()

    def set_tokens():
        g._gallery_token = {'token_id': 'a', 'token_secret': 'b', 'gallery_id': 'c', 'gallery_secret': 'd'}
        g._client.headers[_const.CSRF_TOKEN_HEADER] = 'csrf_token'

    with patch.object(g, 'create', new_callable=AsyncMock, side_effect=set_tokens):
        mock_upload_response = {'files': [{
            'original_url': 'http://image_url',
            'thumbnail_url': 'http://thumbnail_url',
            'url': 'http://web_url',
        }]}
        client.post.side_effect = [mock_upload_response] * 3
        for i in range(3):
            await g._upload_image(f'foo{i}.jpg', 'mock filetuple', None)
            assert g.create.call_args_list == [call()]

@pytest.mark.asyncio
async def test_upload_image_catches_exception_from_create_request(client):
    g = Gallery()
    with patch.object(g, 'create', side_effect=ConnectionError('The Error')):
        for i in range(3):
            sub = await g._upload_image(f'foo{i}.jpg', 'mock filetuple', None)
            assert sub == Submission(filepath=f'foo{i}.jpg', error='The Error')
            assert g.create.call_args_list == [call()] * (i + 1)

@pytest.mark.asyncio
async def test_upload_image_catches_exception_from_upload_request(client):
    g = Gallery()
    g._gallery_token = {'token_id': 'a', 'token_secret': 'b', 'gallery_id': 'c', 'gallery_secret': 'd'}
    g._client.headers[_const.CSRF_TOKEN_HEADER] = 'csrf_token'
    client.post.side_effect = ConnectionError('The Error')
    sub = await g._upload_image('foo.jpg', 'mock filetuple', None)
    assert sub == Submission(filepath='foo.jpg', error='The Error')

@pytest.mark.asyncio
async def test_upload_image_makes_correct_upload_request(client):
    g = Gallery()
    g._gallery_token = {'token_id': 'a', 'token_secret': 'b', 'gallery_id': 'c', 'gallery_secret': 'd'}
    g._client.headers[_const.CSRF_TOKEN_HEADER] = 'csrf_token'
    client.post.return_value = {'files': [{
        'original_url': 'http://image_url',
        'thumbnail_url': 'http://thumbnail_url',
        'url': 'http://web_url',
    }]}
    await g._upload_image('foo.jpg', 'mock filetuple', None)
    assert client.post.call_args_list == [call(
        url=_const.PROCESS_URL,
        data={
            'token_id': 'a',
            'token_secret': 'b',
            'gallery_id': 'c',
            'gallery_secret': 'd',
            'content_type': _const.CONTENT_TYPES['family'],
            'thumbnail_size': _const.THUMBNAIL_SIZES_KEEP_ASPECT[100],
            'comments_enabled': '0',
        },
        files={'files[]': 'mock filetuple'},
        json=True,
    )]

@pytest.mark.parametrize(
    argnames='unexpected_response, exp_cause, exp_cause_msg',
    argvalues=(
        ('foo', TypeError, (
            "string indices must be integers, not 'str'"
            if sys.version_info >= (3, 11)
            else
            'string indices must be integers'
        )),
        ({'foo': [1, 2, 3]}, KeyError, "'files'"),
        ({'files': [1, 2, 3]}, TypeError, "'int' object is not subscriptable"),
        ({'files': [{'foo': 1, 'bar': 2}]}, KeyError, "'original_url'"),
    ),
)
@pytest.mark.asyncio
async def test_upload_image_catches_unexpected_response(unexpected_response, exp_cause, exp_cause_msg, client):
    g = Gallery()
    g._gallery_token = {'token_id': 'a', 'token_secret': 'b', 'gallery_id': 'c', 'gallery_secret': 'd'}
    g._client.headers[_const.CSRF_TOKEN_HEADER] = 'csrf_token'
    client.post.return_value = unexpected_response
    with pytest.raises(RuntimeError, match=rf'Unexpected response: {re.escape(repr(unexpected_response))}$') as exc_info:
        await g._upload_image('foo.jpg', 'mock filetuple', None)
    assert isinstance(exc_info.value.__cause__, exp_cause)
    assert str(exc_info.value.__cause__) == exp_cause_msg

@pytest.mark.asyncio
async def test_upload_image_returns_submission(client):
    g = Gallery()
    g._gallery_token = {'token_id': 'a', 'token_secret': 'b', 'gallery_id': 'c', 'gallery_secret': 'd'}
    g._client.headers[_const.CSRF_TOKEN_HEADER] = 'csrf_token'
    client.post.return_value = {'files': [{
        'original_url': 'http://image_url',
        'thumbnail_url': 'http://thumbnail_url',
        'url': 'http://web_url',
    }]}
    sub = await g._upload_image('foo.jpg', 'mock filetuple', None)
    assert sub == Submission(
        filepath='foo.jpg',
        image_url='http://image_url',
        thumbnail_url='http://thumbnail_url',
        web_url='http://web_url',
        gallery_url=g.url,
        edit_url=g.edit_url,
    )


@pytest.mark.asyncio
async def test_upload(client):
    g = Gallery()
    mock_prepare = Mock(return_value=[('mock filepath', 'mock filetuple', 'mock error')])
    with patch.multiple(g, _prepare=mock_prepare, _upload_image=AsyncMock()):
        submission = await g.upload('path/to/foo.jpg')
        assert g._prepare.call_args_list == [call('path/to/foo.jpg')]
        assert g._upload_image.call_args_list == [
            call('mock filepath', 'mock filetuple', 'mock error'),
        ]
        assert submission is g._upload_image.return_value


@pytest.mark.asyncio
async def test_Gallery_add(client, mocker):
    g = Gallery()
    filepaths = ('path/to/foo.jpg', 'bar.jpg', 'something/baz.jpg')
    mock_prepare = Mock(return_value=[
        (f'{filepath}: mock filepath', f'{filepath}: mock filetuple', f'{filepath}: mock error')
        for filepath in filepaths
    ])
    mock_upload_image = AsyncMock(side_effect=[
        f'{filepath} submission'
        for filepath in filepaths
    ])
    with patch.multiple(g, _prepare=mock_prepare, _upload_image=mock_upload_image):
        submissions = [s async for s in g.add(filepaths)]
        assert g._prepare.call_args_list == [call(*filepaths)]
    assert submissions == [
        'path/to/foo.jpg submission',
        'bar.jpg submission',
        'something/baz.jpg submission',
    ]


def test_repr(client):
    g = Gallery(
        title='Foo',
        thumb_width=123,
        square_thumbs=True,
        adult=True,
        comments_enabled=True,
    )
    assert repr(g) == ("Gallery(title='Foo', thumb_width=150, "
                       "square_thumbs=True, adult=True, comments_enabled=True)")
