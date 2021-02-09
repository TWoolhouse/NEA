from path import PATH
from single import Singleton
import database as db
import loader

__all__ = ["Database"]

class Database(metaclass=Singleton):

    def __init__(self):
        self._db = db.DatabaseAsync(PATH+"database.db")

    def new(self):
        self._db.new()

    async def repopulate(self):
        game = await self._db.table("Game", db.Column("name", db.Type.STR, db.Type.NULL), db.Column("file", db.Type.STR, db.Type.NULL))
        user = await self._db.table("User", db.Column("name", db.Type.STR, db.Type.NULL), db.Column("password", db.Type.STR, db.Type.NULL))

        # Default Users
        await self._db().insert(user, "admin", "password")

        # Games
        await self._db().insert(game, "Pong", "g_pong.py")

    async def __aenter__(self):
        await self._db.__aenter__()
        return self
    async def __aexit__(self, *args):
        return await self._db.__aexit__(*args)

    def login(self, username: str, password: str) -> int:
        return self._db.selectID(self._db["User"], db.Condition(username), db.Condition(password))

    async def register(self, username: str, password: str) -> int:
        return await self._db().insert(self._db["User"], username, password)
