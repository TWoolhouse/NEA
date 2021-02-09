import os
import caching
import importlib
from path import PATH

FILE = "game.py"
DIR = "games/"
DIRP = PATH + DIR

def new(filename: str=FILE):
    with open(DIRP+filename, "w") as file:
        file.write("pass\n")
    return importlib.import_module(DIR.replace("/", ".")+filename.split(".", 1)[0])

def validate(module) -> bool:
    if hasattr(module, "main"):
        return True
    return False

class GameSet:
    def __init__(self):
        self.names = set()
        self.active: str = None
        self._module = new()
        self.reload()

    def reload(self) -> bool:
        module = importlib.reload(self._module)
        self._valid = validate(module)
        if self._valid:
            self._module = module
        else:
            self._valid = validate(self._module)
        return self._valid

    def get(self):
        return self._module

    def valid(self) -> bool:
        return self._valid

def read(filename: str) -> bytes:
    with open(DIRP+filename+"/main.py", "rb") as file:
        return file.read()

def write(data: bytes):
    with open(DIRP+FILE, "wb") as file:
        file.write(data)

@caching.cache(1)
def find_file(name: str) -> str:
    filename = "g_{}".format(name)
    if filename in os.listdir(DIRP) and "main.py" in os.listdir(DIRP+filename):
        return filename
    return False

@caching.cache(1)
def list_avalible() -> list[str]:
    return [filename[2:] for filename in os.listdir(DIRP) if filename.startswith("g_")]
