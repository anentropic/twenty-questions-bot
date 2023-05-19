from typing import cast

from sqladmin.authentication import AuthenticationBackend
from starlette.requests import Request
from starlette.responses import RedirectResponse

from .repository import Repository


class AdminAuth(AuthenticationBackend):
    login_max_age = 60 * 60 * 24 * 1  # in seconds
    salt = "admin_auth"

    def __init__(self, repository: Repository, secret_key: str):
        super().__init__(secret_key=secret_key)
        self.db = repository

    async def login(self, request: Request) -> bool:
        form = await request.form()
        username, password = cast(str, form["username"]), cast(str, form["password"])
        admin = self.db.get_admin_by_username(username)
        if not admin:
            return False
        if not admin.password == password:
            return False

        request.session.update({"adminuser": username})
        return True

    async def logout(self, request: Request) -> bool:
        request.session.clear()
        return True

    async def authenticate(self, request: Request) -> RedirectResponse | None:
        try:
            username = cast(str, request.session["adminuser"])
            admin = self.db.get_admin_by_username(username)
        except KeyError:
            admin = None
        if not admin:
            return RedirectResponse(request.url_for("admin:login"), status_code=302)
        return None
