import pytest

from pyimgbox import Submission


def test_Submission_needs_success_key():
    with pytest.raises(TypeError, match=r"required keyword-only argument: 'success'$"):
        Submission(x='y')

def test_Submission_gets_unknown_key():
    with pytest.raises(AssertionError, match=r"^Unknown key: 'x'$"):
        Submission(success=False, x='y')

def test_Submission_gets_failure_and_no_error():
    with pytest.raises(AssertionError, match=r"^Missing key: 'error'$"):
        Submission(success=False, filename='foo')

def test_Submission_gets_conflicting_success_and_error():
    with pytest.raises(AssertionError, match=r"^Conflicting keys: 'error', 'success'$"):
        Submission(success=True, error='Huh?')

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
            Submission(success=True, **keys)

def test_Submission_gets_valid_success_arguments():
    assert Submission(
        success=True,
        filename='Foo.jpg',
        filepath='path/to/Foo.jpg',
        image_url='https://foo.bar/asdf.jpg',
        thumbnail_url='https://foo.bar/asdf_t.jpg',
        web_url='https://foo.bar/asdf',
        gallery_url='https://foo.bar/fdsa',
        edit_url='https://foo.bar/fdsa/edit'
    ) == {'success': True,
          'error': None,
          'filename': 'Foo.jpg',
          'filepath': 'path/to/Foo.jpg',
          'image_url': 'https://foo.bar/asdf.jpg',
          'thumbnail_url': 'https://foo.bar/asdf_t.jpg',
          'web_url': 'https://foo.bar/asdf',
          'gallery_url': 'https://foo.bar/fdsa',
          'edit_url': 'https://foo.bar/fdsa/edit'}

def test_Submission_gets_valid_error_arguments():
    assert Submission(
        success=False,
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
