from aplus_auth.auth.django import AnonymousUser, ServiceAuthentication, Request


class User(AnonymousUser):
    def __init__(self, id, perms):
        self.id = id
        self.perms = perms
        self.is_authenticated = True


class Authentication(ServiceAuthentication[AnonymousUser]):
    def get_user(self, request: Request, id: str, payload: dict) -> User:
        return User(id, "")