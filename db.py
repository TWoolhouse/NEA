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
        user = await self._db.table("User", db.Column("name", db.tp.STR, db.tp.NULL), db.Column("password", db.tp.STR, db.tp.NULL))
        game = await self._db.table("Game", db.Column("name", db.tp.STR, db.tp.NULL), db.Column("folder", db.tp.STR, db.tp.NULL))
        ai = await self._db.table("AI", db.Column.Foreign("gid", game), db.Column("name", db.tp.STR, db.tp.NULL), db.Column("filename", db.tp.STR, db.tp.NULL))
        score = await self._db.table("Score", db.Column.Foreign("uid", user), db.Column.Foreign("gid", game), db.Column.Foreign("aid", ai), db.Column("value", db.tp.INT, db.tp.NULL))

        # Default Users
        await self.register("annon", "annon_user_password")

    async def _add_games_ai(self, game: tuple[str, str], *ai: tuple[str, str]):
        gid = await self.create_game(*game)
        for i in ai:
            await self.create_ai(gid, *i)

    async def __aenter__(self):
        await self._db.__aenter__()
        return self
    async def __aexit__(self, *args):
        return await self._db.__aexit__(*args)

    async def login(self, username: str, password: str) -> int:
        return (await self._db().select(self._db["User"], db.Condition(username, "name"), db.Condition(password, "password"), cols=["id"]))(1)[0]
    async def register(self, username: str, password: str) -> int:
        return await self._db().insert(self._db["User"], username, password)

    async def user_exists(self, username: str) -> bool:
        return (await self._db().select(self._db["User"], db.Condition(username, "name"), cols=["id"]))(1)

    async def game(self, id: int) -> list[str, str]:
        return (await self._db().select(self._db["Game"], id, cols=["name", "folder"]))(1)
    async def ai(self, id: int) -> list[str, str]:
        return (await self._db().select(self._db["AI"], id, cols=["name", "filename"]))(1)

    async def game_list(self) -> list[tuple[int, str]]:
        return (await self._db().select(self._db["Game"], cols=["id", "name"]))(None)
    async def ai_list(self, game: int) -> list[tuple[int, str]]:
        return (await self._db().select(self._db["Ai"], db.Condition(game, "gid"), cols=["id", "name"]))(None)

    async def create_game(self, name: str, folder: str) -> int:
        return await self._db().insert(self._db["Game"], name, folder)
    async def create_ai(self, game: int, name: str, filename: str) -> int:
        return await self._db().insert(self._db["AI"], game, name, filename)
    async def create_score(self, user: int, game: int, ai: int, score: int):
        return await self._db("score").insert(self._db["Score"], user, game, ai, score)

    async def ai_game(self, id: int) -> list[str, str]:
        return await self.game((await self._db().select(self._db["AI"], id, cols=["gid"]))(1)[0])

    async def score_list(self, type: str="all", data=None):
        dbi = self._db("get_score")
        tu, tg, ta, ts = self._db["User"], self._db["Game"], self._db["AI"], self._db["Score"]
        if type in ("user", "game", "ai"):
            tb = {"user": tu, "game": tg, "ai": ta}
            await dbi.select((ts, ta, tg, tu),
                db.Condition(tb[type]["id"], data),
                cols=(
                        tu["name"], tg["name"], ta["name"], ts["value"]
                ), order=(ts["value"], -1)
            )
        else: # All
            await dbi.select((ts, ta, tg, tu), cols=(
                tu["name"], tg["name"], ta["name"], ts["value"]
            ), order=(ts["value"], -1))

        SIZE = 10
        while True:
            res = dbi.fetch(SIZE)
            yield res
            if len(res) < SIZE:
                break
