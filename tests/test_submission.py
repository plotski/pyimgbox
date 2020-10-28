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
