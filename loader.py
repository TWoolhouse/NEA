import os
import importlib
from single import Singleton
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

class Module:
    def __init__(self):
        self.names = ["None"]
        self._active = 0
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

    def active(self) -> str:
        self.names[self._active]

    def valid(self) -> bool:
        return self._valid

def read(filename: str) -> bytes:
    with open(filename, "rb") as file:
        return file.read(DIRP+filename)

def write(data: bytes):
    with open(DIRP+FILE, "wb") as file:
        file.write(data)

def find_file(name: str) -> str:
    filename = "g_{}.py".format(name)
    if filename in os.listdir(DIRP):
        return filename
    return False

def list_avalible() -> str:
    for filename in os.listdir(DIRP):
        if filename.startswith("g_") and filename.endswith(".py"):
            yield filename
