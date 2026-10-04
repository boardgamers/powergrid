"""Public rule-based search budget, shared by the arena and CPU worker."""

SCOPES = ["all", "recharged-sealed"]


def search_enabled(scope, variant, sealed):
    if scope not in SCOPES:
        raise ValueError(f"Unknown search scope: {scope}")
    return scope == "all" or (variant == "recharged" and bool(sealed))
