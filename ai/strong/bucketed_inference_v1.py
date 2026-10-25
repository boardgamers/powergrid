"""Experimental action-count batching; no model, feature or move-order changes."""


def predict_bucketed(original, model, rows, batch_size=64):
    if not isinstance(batch_size, int) or batch_size < 1:
        raise ValueError('Invalid batch size')
    order = sorted(range(len(rows)), key=lambda i: len(rows[i]['actions']))
    choices = original(model, [rows[i] for i in order], batch_size=batch_size)
    if len(choices) != len(rows):
        raise ValueError('Incomplete prediction batch')
    restored = [None] * len(rows)
    for index, choice in zip(order, choices):
        restored[index] = choice
    return restored


def padded_actions(rows, batch_size=64):
    counts = [len(row['actions']) for row in rows]
    return sum(len(part) * max(part) for start in range(0, len(counts), batch_size)
               if (part := counts[start:start + batch_size]))
