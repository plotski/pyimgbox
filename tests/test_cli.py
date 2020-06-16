import json
from unittest.mock import Mock, call, patch

from pyimgbox import _cli


class MockSubmission(dict):
    def __getattr__(self, name):
        return self[name]


@patch('pyimgbox.Gallery')
@patch('pyimgbox._cli._text_output')
def test_run_passes_arguments_to_Gallery(mock_text_output, mock_Gallery):
    mock_text_output.return_value = 0
    assert _cli.run(['foo.jpg', 'bar.jpg', '--title', 'Foo and Bar',
                     '--adult', '--comments',
                     '--square-thumbs', '--thumb-width', '500']) == 0
    assert mock_Gallery.call_args_list == [
        call(title='Foo and Bar',
             adult=True, comments_enabled=True,
             square_thumbs=True, thumb_width=500)
    ]

@patch('pyimgbox.Gallery')
@patch('pyimgbox._cli._text_output')
def test_run_handles_RuntimeError_from_text_output(mock_text_output, mock_Gallery):
    mock_text_output.side_effect = RuntimeError('Argh')
    assert _cli.run(['foo.jpg']) == 100
    assert mock_text_output.call_args_list == [call(mock_Gallery(), ['foo.jpg'])]

@patch('pyimgbox.Gallery')
@patch('pyimgbox._cli._json_output')
def test_run_handles_RuntimeError_from_json_output(mock_json_output, mock_Gallery):
    mock_json_output.side_effect = RuntimeError('Argh')
    assert _cli.run(['--json', 'foo.jpg']) == 100
    assert mock_json_output.call_args_list == [call(mock_Gallery(), ['foo.jpg'])]


def test_text_output_handles_ConnectionError_from_creation(capsys):
    mock_gallery = Mock()
    mock_gallery.create.side_effect = ConnectionError('Oops')
    assert _cli._text_output(mock_gallery, ['foo.jpg']) == 1
    cap = capsys.readouterr()
    assert cap.err == 'Oops\n'
    assert cap.out == ''

def test_text_output_handles_error_from_addition(capsys):
    mock_gallery = Mock(url='<Gallery URL>', edit_url='<Edit URL>')
    mock_gallery.add.return_value = (
        MockSubmission(filename='foo.jpg', success=False, error='Oops'),
    )
    assert _cli._text_output(mock_gallery, ['foo.jpg']) == 2
    cap = capsys.readouterr()
    assert cap.err == ''
    assert cap.out == ('Gallery: <Gallery URL>\n'
                       '   Edit: <Edit URL>\n'
                       '* foo.jpg\n'
                       '  Oops\n')

def test_text_output_prints_submissions(capsys):
    mock_gallery = Mock(url='<Gallery URL>', edit_url='<Edit URL>')
    mock_gallery.add.return_value = (
        MockSubmission(filename='foo.jpg', success=True, error=None,
                       image_url='img/foo', thumbnail_url='thumb/foo', web_url='web/foo'),
        MockSubmission(filename='bar.jpg', success=True, error=None,
                       image_url='img/bar', thumbnail_url='thumb/bar', web_url='web/bar'),
    )
    assert _cli._text_output(mock_gallery, ['foo.jpg', 'bar.jpg']) == 0
    cap = capsys.readouterr()
    assert cap.err == ''
    assert cap.out == ('Gallery: <Gallery URL>\n'
                       '   Edit: <Edit URL>\n'
                       '* foo.jpg\n'
                       '      Image: img/foo\n'
                       '  Thumbnail: thumb/foo\n'
                       '    Webpage: web/foo\n'
                       '* bar.jpg\n'
                       '      Image: img/bar\n'
                       '  Thumbnail: thumb/bar\n'
                       '    Webpage: web/bar\n')


def test_json_output_handles_ConnectionError_from_creation(capsys):
    mock_gallery = Mock()
    mock_gallery.create.side_effect = ConnectionError('Oops')
    assert _cli._json_output(mock_gallery, ['foo.jpg']) == 1
    cap = capsys.readouterr()
    assert cap.err == ''
    assert json.loads(cap.out) == {'success': False, 'error': 'Oops',
                                   'gallery_url': None, 'edit_url': None,
                                   'images': []}

def test_json_output_handles_error_from_addition(capsys):
    mock_gallery = Mock(url='<Gallery URL>', edit_url='<Edit URL>')
    mock_gallery.add.return_value = (
        MockSubmission(filename='foo.jpg', success=False, error='Oops'),
    )
    assert _cli._json_output(mock_gallery, ['foo.jpg']) == 2
    cap = capsys.readouterr()
    assert cap.err == ''
    assert json.loads(cap.out) == {'success': True, 'error': None,
                                   'gallery_url': '<Gallery URL>', 'edit_url': '<Edit URL>',
                                   'images': [
                                       MockSubmission(filename='foo.jpg', success=False, error='Oops')
                                   ]}

def test_json_output_prints_submissions(capsys):
    mock_gallery = Mock(url='<Gallery URL>', edit_url='<Edit URL>')
    mock_gallery.add.return_value = (
        MockSubmission(filename='foo.jpg', success=True, error=None,
                       image_url='img/foo', thumbnail_url='thumb/foo', web_url='web/foo'),
        MockSubmission(filename='bar.jpg', success=True, error=None,
                       image_url='img/bar', thumbnail_url='thumb/bar', web_url='web/bar'),
    )
    assert _cli._json_output(mock_gallery, ['foo.jpg', 'bar.jpg']) == 0
    cap = capsys.readouterr()
    assert cap.err == ''
    assert json.loads(cap.out) == {'success': True, 'error': None,
                                   'gallery_url': '<Gallery URL>', 'edit_url': '<Edit URL>',
                                   'images': [
                                       MockSubmission(filename='foo.jpg', success=True, error=None,
                                                      image_url='img/foo',
                                                      thumbnail_url='thumb/foo',
                                                      web_url='web/foo'),
                                       MockSubmission(filename='bar.jpg', success=True, error=None,
                                                      image_url='img/bar',
                                                      thumbnail_url='thumb/bar',
                                                      web_url='web/bar'),
                                   ]}
