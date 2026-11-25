import json
from importlib.resources import files


def catalogue():
    return json.loads(files("inventory").joinpath("catalogue.json").read_text())


def distance(a, b):
    previous = list(range(len(b) + 1))
    for i, left in enumerate(a, 1):
        current = [i]
        for j, right in enumerate(b, 1):
            current.append(min(previous[j] + 1, current[-1] + 1, previous[j - 1] + (left != right)))
        previous = current
    return previous[-1]


def suggestions(value, items):
    if not value or value in items:
        return []
    ranked = sorted((distance(value, key), key) for key in items)
    return [key for steps, key in ranked if steps == ranked[0][0] and steps <= 1][:4]
