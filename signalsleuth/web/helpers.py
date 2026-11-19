"""Small template/view helpers."""


def _stringify_dates(row, keys):
    """Return a shallow copy of dict row with date fields as strings for templates."""
    if not row:
        return row
    out = dict(row)
    for k in keys:
        if k in out and out[k] is not None:
            out[k] = str(out[k])
    return out
