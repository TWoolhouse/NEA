import node
import db
import loader

__all__ = ["Server", "Client"]

PORT = 603

def encode(func):
    def encode_data(*args, **kwargs):
        return "\a".join(map(str, func(*args, **kwargs)))
    return encode_data

class Server:
    Database = db.Database()

    def __init__(self):
        self.__node = node.Server("", PORT, limit=4, dispatchers=(self.PING, self.GAME, self.GLIST, self.DATABASE), password="nea")

    def __enter__(self):
        self.__node.open()
        return self
    def __exit__(self, exc_type, exc_value, traceback):
        return self.__node.close()

    class PING(node.Dispatch):
        def handle(self):
            print(self.data)
            self.node.send(self.data)

    class GLIST(node.Dispatch):
        def handle(self):
            print("Request Game List")
            glist = loader.list_avalible()
            self.node.send(len(glist), "GLIST")
            for element in glist:
                self.node.send(element, "DATA", node.Tag("GLIST"))

    class GAME(node.Dispatch):
        def handle(self):
            print("Game Request:", self.data.data)
            if filename := loader.find_file(self.data.data):
                print("Game File:", self.data.data)
                return self.node.send(loader.read(filename), "GAME", "BIN")
            print("Game Not Found:", self.data.data)
            return self.node.send(False, "GAME", node.Tag("FALSE"))

    class DATABASE(node.Dispatch):
        def handle(self):
            request = self.data.tags[0].lower()
            data = self.data.data.split("\a")
            print("Database Request:", request, *data)
            self.node.send(getattr(self, "h_"+request)(*data), "DATABASE", node.Tag(request))

        def h_login(self, username: str, password: str) -> int:
            return int(Server.Database.login(username, password))
        def h_register(self, username: str, password: str) -> int:
            return int(Server.Database.register(username, password))

class Client:

    def __init__(self, addr: str):
        self.__node = node.Client(addr, PORT, dispatch=(self.PING, self.GAME, self.GLIST, self.DATABASE), password="nea")
        self.send = self.__node.send
        # self.join = self.__node.join
        self.recv = self.__node.recv

    def conn_name(self) -> str:
        return "{}:{}".format(self.__node.addr, self.__node.port)
    def is_open(self) -> bool:
        return bool(self.__node)

    def open(self):
        self.__node.open()
    def close(self):
        return self.__node.close()

    def __enter__(self):
        self.open()
        return self
    def __exit__(self, exc_type, exc_value, traceback):
        return self.close()

    class PING(node.Dispatch, output=True):
        def handle(self):
            print(self.data)

    class GLIST(node.Dispatch, output=True):
        def handle(self):
            return [i.data for i in self.node.recv(node.Tag("GLIST"), wait=int(self.data.data))]

    class GAME(node.Dispatch, output=True):
        def handle(self):
            if "FALSE" in self.data.tags:
                return False
            loader.write(self.data.data)
            return True

    class DATABASE(node.Dispatch, output=True):
        def handle(self):
            return getattr(self, "h_"+self.data.tags[0].lower())(*self.data.data.split("\a"))

        def h_login(self, value: str):
            return int(value)
        def h_register(self, value: str):
            return int(value)

    def glist(self):
        self.__node.send(None, "GLIST")
        return self.__node.recv("GLIST", wait=True)[0].data

    def game(self, name: str):
        self.__node.send(name.lower(), "GAME")
        return self.__node.recv("GAME", wait=True)[0].data

    def database(self, req: str, *args):
        self.__node.send("\a".join(map(str, args)), "DATABASE", node.Tag(req))
        return self.__node.recv("DATABASE", node.Tag(req), wait=True)[0].data