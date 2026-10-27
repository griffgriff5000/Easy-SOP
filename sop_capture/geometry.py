def screen_to_image(point, bounds, size):
    left, top, right, bottom = bounds
    width, height = right - left, bottom - top
    if width <= 0 or height <= 0 or min(size) <= 0:
        raise ValueError("Invalid capture dimensions")
    x, y = point
    if not left <= x < right or not top <= y < bottom:
        return None
    return ((x - left) * size[0] / width, (y - top) * size[1] / height)


def fit_rect(size, available):
    if min(size) <= 0:
        raise ValueError("Invalid image size")
    scale = min(available[0] / size[0], available[1] / size[1])
    return size[0] * scale, size[1] * scale
