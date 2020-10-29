import pytest

from pyimgbox import Submission


def test_Submission_gets_unknown_key():
    with pytest.raises(AssertionError, match=r"^Unknown key: 'x'$"):
        Submission(x='y')


@pytest.mark.parametrize(
    argnames='key',
    argvalues=('filepath', 'image_url', 'thumbnail_url', 'web_url', 'gallery_url', 'edit_url'),
)
def test_Submission_required_argument_on_success(key):
    with pytest.raises(AssertionError, match=rf"^Missing key: '{key}'$"):
        kwargs = {
            'filepath': 'path/to/Foo.jpg',
            'image_url': 'https://foo.bar/asdf.jpg',
            'thumbnail_url': 'https://foo.bar/asdf_t.jpg',
            'web_url': 'https://foo.bar/asdf',
            'gallery_url': 'https://foo.bar/asdf/gallery',
            'edit_url': 'https://foo.bar/asdf/edit',
        }
        del kwargs[key]
        Submission(**kwargs)


def test_Submission_no_required_arguments_on_error():
    assert Submission(
        error='Trouble is afoot!',
    ) == {'success': False,
          'error': 'Trouble is afoot!',
          'filename': None,
          'filepath': None,
          'image_url': None,
          'thumbnail_url': None,
          'web_url': None,
          'gallery_url': None,
          'edit_url': None}


def test_Submission_gets_valid_success_arguments():
    assert Submission(
        filepath='path/to/Foo.jpg',
        image_url='https://foo.bar/asdf.jpg',
        thumbnail_url='https://foo.bar/asdf_t.jpg',
        web_url='https://foo.bar/asdf',
        gallery_url='https://foo.bar/fdsa',
        edit_url='https://foo.bar/fdsa/edit'
    ) == {
        'success': True,
        'error': None,
        'filename': 'Foo.jpg',
        'filepath': 'path/to/Foo.jpg',
        'image_url': 'https://foo.bar/asdf.jpg',
        'thumbnail_url': 'https://foo.bar/asdf_t.jpg',
        'web_url': 'https://foo.bar/asdf',
        'gallery_url': 'https://foo.bar/fdsa',
        'edit_url': 'https://foo.bar/fdsa/edit',
    }


def test_Submission_getattr_key_with_None_value():
    s = Submission(error='Argh')
    assert s.filename is None
    assert s.filepath is None
    assert s.image_url is None
    assert s.thumbnail_url is None
    assert s.web_url is None
    assert s.gallery_url is None
    assert s.edit_url is None


def test_Submission_getattr_unknown_key():
    s = Submission(
        filepath='path/to/Foo.jpg',
        image_url='https://foo.bar/asdf.jpg',
        thumbnail_url='https://foo.bar/asdf_t.jpg',
        web_url='https://foo.bar/asdf',
        gallery_url='https://foo.bar/fdsa',
        edit_url='https://foo.bar/fdsa/edit'
    )
    with pytest.raises(AttributeError, match=r"^Submission object has no attribute 'foo'$"):
        s.foo


def test_Submission_repr():
    s = Submission(
        filepath='path/to/Foo.jpg',
        image_url='https://foo.bar/asdf.jpg',
        thumbnail_url='https://foo.bar/asdf_t.jpg',
        web_url='https://foo.bar/asdf',
        gallery_url='https://foo.bar/fdsa',
        edit_url='https://foo.bar/fdsa/edit'
    )
    assert repr(s) == (
        "Submission("
        "success=True, "
        "filepath='path/to/Foo.jpg', "
        "filename='Foo.jpg', "
        "image_url='https://foo.bar/asdf.jpg', "
        "thumbnail_url='https://foo.bar/asdf_t.jpg', "
        "web_url='https://foo.bar/asdf', "
        "gallery_url='https://foo.bar/fdsa', "
        "edit_url='https://foo.bar/fdsa/edit'"
        ")"
    )
