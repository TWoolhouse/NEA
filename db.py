from path import PATH
from single import Singleton
import database as db
import loader

__all__ = ["Database"]

class Database(metaclass=Singleton):

    def __init__(self):
        self.__db = db.ThreadDatabase(PATH+"database")

    def new(self):
        self.__db.new()

    def repopulate(self):
        game = self.__db.table("Game", db.Column("name", db.Type.String, db.Type.NotNull), db.Column("file", db.Type.String, db.Type.NotNull))
        user = self.__db.table("User", db.Column("name", db.Type.String, db.Type.NotNull), db.Column("password", db.Type.String, db.Type.NotNull))

        # Default Users
        self.__db.insert(user, "admin", "password")

        # Games
        self.__db.insert(game, "Pong", "g_pong.py")

    def __enter__(self):
        self.__db.open()
        return self
    def __exit__(self, exc_type, exc_value, traceback):
        self.__db.close()

    def login(self, username: str, password: str) -> int:
        return self.__db.selectID(self.__db["User"], db.Condition(username), db.Condition(password))

    def register(self, username: str, password: str) -> int:
        return self.__db.insert(self.__db["User"], username, password, id=True)