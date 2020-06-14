from unittest.mock import Mock, call

import pytest
import requests

from pyimgbox import _const, _utils


def test_get_succeeds():
    mock_session = Mock()
    mock_session.get.return_value.text = '<html>'
    response = _utils.get(mock_session, 'https://foo', timeout=123, bar='asdf')
    assert response == '<html>'
    assert mock_session.get.call_args_list == [
        call('https://foo', timeout=123, bar='asdf')]

def test_get_raises_ConnectionError():
    mock_session = Mock()
    mock_session.get.side_effect = requests.ConnectionError('Nah')
    with pytest.raises(ConnectionError, match=fr'^Failed to connect to {_const.SERVICE_DOMAIN}$'):
        _utils.get(mock_session, 'https://foo', bar='asdf')
    assert mock_session.get.call_args_list == [
        call('https://foo', timeout=_const.DEFAULT_TIMEOUT, bar='asdf')]


def test_post_json_succeeds():
    mock_session = Mock()
    mock_session.post.return_value.json.return_value = {'this': 'is', 'j': 'son'}
    response = _utils.post_json(mock_session, 'https://foo', timeout=123, bar='asdf')
    assert response == {'this': 'is', 'j': 'son'}
    assert mock_session.post.call_args_list == [
        call('https://foo', timeout=123, bar='asdf')]

def test_post_json_raises_ConnectionError():
    mock_session = Mock()
    mock_session.post.side_effect = requests.ConnectionError('Nah')
    with pytest.raises(ConnectionError, match=fr'^Failed to connect to {_const.SERVICE_DOMAIN}$'):
        _utils.post_json(mock_session, 'https://foo', bar='asdf')
    assert mock_session.post.call_args_list == [
        call('https://foo', timeout=_const.DEFAULT_TIMEOUT, bar='asdf')]

def test_post_json_raises_ValueError():
    mock_session = Mock()
    mock_session.post.return_value.text = 'This is not JSON.'
    mock_session.post.return_value.json.side_effect = ValueError('Not JSON')
    with pytest.raises(ValueError, match=r'^Not JSON: This is not JSON.$'):
        _utils.post_json(mock_session, 'https://foo', bar='asdf')
    assert mock_session.post.call_args_list == [
        call('https://foo', timeout=_const.DEFAULT_TIMEOUT, bar='asdf')]


def test_find_closest_number():
    numbers = (10, 20, 30)
    for n in (-10, 0, 9, 10, 11, 14):
        assert _utils.find_closest_number(n, numbers) == 10
    for n in (16, 19, 20, 21, 24):
        assert _utils.find_closest_number(n, numbers) == 20
    for n in range(26, 50):
        assert _utils.find_closest_number(n, numbers) == 30
