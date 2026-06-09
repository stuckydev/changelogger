COOKIE_MAX_AGE = 60 * 60 * 24 * 365


def cookie_kwargs(max_age: int = COOKIE_MAX_AGE) -> dict:
    return {
        "max_age": max_age,
        "httponly": False,
        "samesite": "lax",
        "path": "/",
    }
