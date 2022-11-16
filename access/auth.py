from aplus_auth.auth.django import AnonymousUser, ServiceAuthentication, Request


class User(AnonymousUser):
    def __init__(self, id, perms):
        self.id = id
        self.perms = perms
        self.is_authenticated = True

    def __str__(self) -> str:
        return str(self.id)

    def __repr__(self) -> str:
        return f"User(id={self.id}, perms={self.perms})"


class Authentication(ServiceAuthentication[AnonymousUser]):
    def get_user(self, request: Request, id: str, payload: dict) -> User:
        return User(id, "")
