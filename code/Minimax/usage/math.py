from usage.score import SCORE

threshold = 1.15


def equal(a, b):
    b = b or 0.01
    return ((a >= b / threshold) and (a <= b * threshold)) if b >= 0 else \
        ((a >= b * threshold) and (a <= b / threshold))


def great_than(a, b):
    return (a >= (b + 0.1) * threshold) if b >= 0 else (a >= (b + 0.1) / threshold)


def great_or_equal_than(a, b):
    return equal(a, b) or great_than(a, b)


def little_than(a, b):
    return (a <= (b - 0.1) / threshold) if b >= 0 else (a <= (b - 0.1) * threshold)


def little_or_equal_than(a, b):
    return equal(a, b) or little_than(a, b)


def contain_point(arrays, p):
    for i in range(0, len(arrays)):
        a = arrays[i]
        if a[0] == p[0] and a[1] == p[1]:
            return True
    return False


def point_equal(a, b):
    return a[0] == b[0] and a[1] == b[1]


def round_score(score):
    neg = -1 if score < 0 else 1
    _abs = abs(score)
    if _abs <= SCORE["ONE"] / 2:
        return 0
    if SCORE["TWO"] / 2 >= _abs > SCORE["ONE"] / 2:
        return neg * SCORE["ONE"]
    if SCORE["THREE"] / 2 >= _abs > SCORE["TWO"] / 2:
        return neg * SCORE["TWO"]
    if SCORE["THREE"] * 1.5 >= _abs > SCORE["THREE"] / 2:
        return neg * SCORE["THREE"]
    if SCORE["FOUR"] / 2 >= _abs > SCORE["THREE"] * 1.5:
        return neg * SCORE["THREE"] * 2
    if SCORE["FIVE"] / 2 >= _abs > SCORE["FOUR"] / 2:
        return neg * SCORE["FOUR"]
    return neg * SCORE["FIVE"]
