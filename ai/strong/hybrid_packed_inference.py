"""Experimental batch packing; preserve row order and the frozen inference code."""
from contextlib import contextmanager
import hybrid_search as hybrid


def packed_predict(model, rows, group_size, *, predict):
    if type(group_size) is not int or group_size not in (8, 16):
        raise ValueError('Only the two profiled group sizes are admitted')
    if not rows:
        return predict(model, rows, group_size)
    order = sorted(range(len(rows)), key=lambda i: len(rows[i]['actions']))
    choices = [None] * len(rows)
    for start in range(0, len(rows), group_size):
        indices = order[start:start+group_size]
        selected = predict(model, [rows[i] for i in indices], group_size)
        if len(selected) != len(indices):
            raise ValueError('Inference returned the wrong number of choices')
        for i, action in zip(indices, selected):
            choices[i] = action
    return choices


@contextmanager
def batch_layout(name):
    if name not in ('plain64', 'packed16', 'packed8'):
        raise ValueError('Unknown batch layout')
    original = hybrid.predict_batch
    if name != 'plain64':
        group_size = int(name.removeprefix('packed'))

        def predict(model, rows, batch_size=64):
            if batch_size != 64:
                raise ValueError('Unexpected caller batch size')
            return packed_predict(model, rows, group_size, predict=original)

        hybrid.predict_batch = predict
    try:
        yield
    finally:
        hybrid.predict_batch = original
