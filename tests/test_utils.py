from pyimgbox import _utils


def test_find_closest_number():
    numbers = (10, 20, 30)
    for n in (-10, 0, 9, 10, 11, 14):
        assert _utils.find_closest_number(n, numbers) == 10
    for n in (16, 19, 20, 21, 24):
        assert _utils.find_closest_number(n, numbers) == 20
    for n in range(26, 50):
        assert _utils.find_closest_number(n, numbers) == 30
