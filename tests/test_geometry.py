import pytest
from sop_capture.geometry import screen_to_image, fit_rect


def test_negative_monitor_and_scaled_image():
    assert screen_to_image((-1800, 100), (-1920, -100, 0, 980), (960, 540)) == (60, 100)
    assert screen_to_image((300, 150), (0, 0, 600, 300), (1200, 600)) == (600, 300)


def test_outside_and_invalid_bounds():
    assert screen_to_image((-1, 5), (0, 0, 100, 100), (100, 100)) is None
    with pytest.raises(ValueError):
        screen_to_image((0, 0), (0, 0, 0, 0), (100, 100))


def test_fit_keeps_aspect():
    assert fit_rect((2000, 1000), (600, 200)) == (400, 200)
