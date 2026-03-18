ROLE_PRIORITY = {
    "viewer": 10,
    "editor": 20,
    "admin": 30,
    "owner": 40,
}


def has_role(required: str, actual: str) -> bool:
    return ROLE_PRIORITY.get(actual, 0) >= ROLE_PRIORITY.get(required, 999)
