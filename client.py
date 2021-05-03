import gui
import enum
import game
import node
import asyio
import loader
import caching
import website
import functools
import webbrowser
from interface import Interface
from collections import namedtuple
from typing import Callable, Any

class Requests(node.Client):
    def __init__(self, addr: str, port: int):
        super().__init__(addr, port)

    def is_open(func):
        async def only_check_cache_if_open(self, *args, **kwargs):
            if not self:
                return None
            return await func(self, *args, **kwargs)
        return only_check_cache_if_open

    async def open(self):
        if not (await super().open()):
            return False
        cfg = website.config("client.cfg")
        self.send(cfg["connection"]["password"], "PASSWORD")
        if not (await self.recv("PASSWORD"))[0].data:
            print("Password: Incorrect")
            print("Connection Closed")
            return not await self.close()
        await self.login(cfg["user"]["name"], cfg["user"]["password"])

    @is_open
    @caching.cache(1, 5)
    async def download(self, game: int):
        print("Download:", game)
        self.send(game, "GAME")
        data = await self.recv("GAME", node.Tag(game))
        if data and data[0].data:
            loader.write_game(data[0].data)
            return True
        return False

    @is_open
    @caching.cache(1, 5)
    async def download_ai(self, ai: int) -> bytes:
        print("Download AI:", ai)
        self.send(ai, "AI")
        data = await self.recv("AI", node.Tag(ai))
        if data and data[0].data:
            return data[0].data
        return False

    @is_open
    @caching.cache(1, 5)
    async def retrieve_list(self) -> list[tuple[int, str]]:
        print("Retrieve List")
        self.send(b"", "GLIST")
        count = await self.recv("GLIST")
        if count:
            return [i.data for i in await self.recv("GLIST", wait=count[0].data)]

    @is_open
    @caching.cache(1, 15)
    async def retrieve_net_list(self, game: int) -> list[tuple[int, str]]:
        print("Retrieve AI List")
        self.send(game, "AILIST")
        count = await self.recv("AILIST", node.Tag(game))
        if count:
            return [i.data for i in await self.recv("AILIST", node.Tag(game), wait=count[0].data)]

    async def send_score(self, gid: int, aid: int, uid: int, value: int):
        self.send(uid, "DATABASE", node.Tag(gid), node.Tag(aid))
        await self.send(value, "DATABASE_VALUE", node.Tag(gid), node.Tag(aid), node.Tag(uid))

    @is_open
    @caching.cache(1, 30)
    async def login(self, name: str, password: str) -> int:
        self.send(name, "LOGIN")
        self.send(password, "LOGIN_PASSWORD")
        return (await self.recv("LOGIN"))[0].data

class GuiApplication:

    def __init__(self, client: 'Client'):
        self.client: Client = client
        self.window = gui.Window("Game Client Menu", resolution=10)
        # Pages
        PageHome(self.window, self, "home")
        PageGame(self.window, self, "games")
        PageLoadGame(self.window, self, "load_game")
        PageSetting(self.window, self, "settings")
        self.window.show_page("home")

    def call(self, func: Callable[..., Any], *args, **kwargs) -> Any:
        self.window.call(functools.partial(func, *args, **kwargs))
    async def acall(self, func: Callable[..., Any], *args, **kwargs) -> Any:
        fut = Interface.loop.create_future()
        def guicallback():
            fut.set_result(func(*args, **kwargs))
        self.window.call(guicallback)
        return await fut

    def main(self):
        self.window.mainloop()

class AppPage(gui.Page):
    def __init__(self, parent: gui.Window, app: GuiApplication, name: str):
        self.app: GuiApplication = app
        super().__init__(parent, name)

    def connect(self):
        pass
    def disconnect(self):
        pass

class PageHome(AppPage):
    def setup(self):
        self.add(gui.tk.Label(self, text="Hello and Welcome"), row=1, column=1, pady=15)
        self.add(gui.tk.Button(self, text="Games", command=lambda: self.show_page("games")), row=2, column=1)
        self.add(gui.tk.Button(self, text="Scoreboard", command=lambda: webbrowser.open_new_tab(f"http://{self.app.client.net.addr}:{self.app.client.net.port + 1}/scoreboard")), row=3, column=1)
        self.add(gui.tk.Button(self, text="Settings", command=lambda: self.show_page("settings")), row=4, column=1)

class PageGame(AppPage):
    def setup(self):
        self.add(gui.tk.Label(self, text="Games"), row=1, column=1, pady=10)
        self.add(gui.tk.Button(self, text="Play: None", command=self.play_game), "current", row=2, column=1, pady=15)
        self.add(gui.tk.Button(self, text="Return", command=lambda: self.show_page("home")), row=99, column=1, pady=15)
        self.edit("current", "state", "disabled")

    def show(self):
        if not self.app.client.net:
            return self.show_page("settings")
        Interface.schedule(self.app.client._retrieve_list())

    def update_listing(self):
        for name in tuple(self.widgets.keys()):
            if name.startswith("g_"):
                self.remove(name)

        for row, game in enumerate(sorted(self.app.client.games.names.items()), start=3):
            wgt = self.add(gui.tk.Button(self, text=game[1].title(), command=gui.cmd(self.app.window["load_game"].load, *game)), f"g_{game[0]}", row=row, column=1, pady=2)
            if self.app.client._active.is_set():
                wgt["state"] = "disabled"

    def play_game(self):
        self.edit("current", "state", "disabled")
        self.edit("current", "text", "Running...")
        Interface.schedule(self.app.client._play_game())
        for name in tuple(self.widgets.keys()):
            if name.startswith("g_"):
                self.edit(name, "state", "disabled")

    def return_game(self):
        self.edit("current", "state", "normal")
        self.edit("current", "text", f"Play: {self.app.client.games.active}")
        for name in tuple(self.widgets.keys()):
            if name.startswith("g_"):
                self.edit(name, "state", "normal")

class PageLoadGame(AppPage):
    def setup(self):
        self.game_id = None
        self.game_name = "None"
        self.net_name = gui.tk.IntVar()
        self.add(gui.tk.Label(self, text="GAME NAME"), "game_name", row=1, column=1, pady=10)
        self.add(gui.tk.Label(self, text="Loading AIs"), "loading", row=2, column=1, pady=5)
        self.add(gui.tk.Radiobutton(self, text="NETWORK NAME", variable=self.net_name, value=0), "net_name_2", row=2, column=1, pady=2)
        self.add(gui.tk.Button(self, text="Download", command=self.load_game), "download", row=98, column=1, pady=5)
        self.add(gui.tk.Button(self, text="Return", command=lambda: self.show_page("games")), row=99, column=1, pady=15)

    def load(self, gid: int, name: str):
        print(self.app.client.net._node)
        if not self.app.client.net:
            return self.show_page("settings")
        self.game_id = gid
        self.game_name = name
        self.edit("game_name", "text", self.game_name.title())
        self.edit("download", "state", "disabled")

        for name in tuple(self.widgets.keys()):
            if name.startswith("net_name_"):
                self.remove(name)

        self["loading"].lift(self["net_name_2"])
        self.net_name.set(0)
        Interface.schedule(self.app.client._retrieve_net_list(self.game_id))

        if not self.app.client._active.is_set():
            self.show_page(self.name)

    def load_nets(self, game: int, nets: list[str]):
        if game != self.game_id:
            return

        if not nets:
            raise ValueError("No Networks")

        for index, net in enumerate(nets, start=2):
            net_wgt = self.add(gui.tk.Radiobutton(self, text=net[1].title(), variable=self.net_name, value=net[0], command=self.set_net_var), f"net_name_{index}", row=index, column=1, pady=2)

        self["loading"].lower(self["net_name_2"])

    def set_net_var(self):
        val = self.net_name.get()
        if val:
            self.edit("download", "state", "normal")

    def show(self):
        self.edit("download", "text", "Download")

    def load_game(self):
        self.parent["games"].edit("current", "state", "disabled")
        self.edit("download", "state", "disabled")
        self.edit("download", "text", "Download...")
        print("Load Game:", self.game_id, self.game_name)
        Interface.schedule(self.app.client._load_game(self.game_id, self.game_name, self.net_name.get()))

class PageSetting(AppPage):
    def setup(self):
        self.add(gui.tk.Label(self, text="Settings"), row=1, column=1, pady=15)
        self.add(gui.tk.Button(self, text="Reconnect", command=lambda: Interface.schedule(self.app.client.net.open()).add_done_callback(lambda x:self.show())), row=2, column=1)
        self.add(gui.tk.Button(self, text="Register Account", command=lambda: webbrowser.open_new_tab(f"http://{self.app.client.net.addr}:{self.app.client.net.port + 1}/register")), row=3, column=1)
        # self.add(gui.tk.Button(self, text="Login: USER", command=self._login), "login", row=4, column=1)

        self.add(gui.tk.Label(self, text="None"), "server", row=5, column=1)
        self.add(gui.tk.Button(self, text="Return", command=lambda: self.show_page("home")), row=99, column=1, pady=15)

    def show(self):
        self.edit("server", "text", "Server: " + (self.app.client.net.addr if self.app.client.net else "Disconnected"))
        cfg = website.config("client.cfg")["user"]
        # self.edit("login", "text", (self.app.client.user.name if self.app.client.user.id != 1 else f"Login: {cfg['name']}"))

    def _login(self):
        if self.app.client.user.id != 1:
            self.app.client.user = User(1, str(None))
            return
        Interface.schedule(self.app.client._login).add_done_callback(lambda x:self.show())

User = namedtuple("User", ("id", "name"))

class Client:
    def __init__(self, addr: str):
        website.config("client.cfg", True, True)
        self.guiapp = GuiApplication(self)
        self.net = Requests(addr, 609)
        self.games = loader.GameSet()
        self.user = User(1, str(None)) # Default User
        game.GameApplication.callback = self._send_to_database

        self._active = asyio.Nevent()

    def main(self):
        Interface.schedule(self.net.open())
        Interface.schedule(self._login())
        try:
            self.guiapp.main()
        finally:
            Interface.schedule(self.net.close())

    async def _retrieve_list(self):
        names = await self.net.retrieve_list()
        if names is None:
            return # Connection Lost
        self.games.names.clear()
        self.games.names.update(names)
        self.guiapp.call(self.guiapp.window["games"].update_listing)

    async def _retrieve_net_list(self, game: int):
        names = await self.net.retrieve_net_list(game)
        if names is None:
            return self.guiapp.call(self.guiapp.window.show_page, "settings")
        self.guiapp.call(self.guiapp.window["load_game"].load_nets, game, names)

    async def _load_game(self, gid: int, name: str, net: int):
        downloads = await Interface.gather(self.net.download(gid), self.net.download_ai(net))
        if all(downloads) and self.games.reload():
            self.games.set_ai(downloads[1])
            self.games.active = name
            self.games.get().main._id = gid
            self.games.ai._id = net
        self.guiapp.call(self.guiapp.window["games"].edit, "current", "text", f"Play: {self.games.active}")
        self.guiapp.call(self.guiapp.window["load_game"].edit, "download", "text", "Done!")
        if self.games.valid():
            self.guiapp.call(self.guiapp.window["games"].edit, "current", "state", "normal")
        else:
            self.guiapp.call(self.guiapp.window["load_game"].edit, "download", "text", "Failed")

    async def _play_game(self):
        if self._active.is_set():
            return
        self._active.set()
        print("Playing Game")
        proc = await self.guiapp.acall(game.run_ai, self.games.get().main, self.games.ai)
        await self.guiapp.acall(game.run_player, self.games.get().main)
        proc.kill()
        print("Game Over")
        self._active.clear()
        self.guiapp.call(self.guiapp.window["games"].return_game)

    async def _send_to_database(self, score: int):
        await self.net.send_score(self.games.get().main._id, self.games.ai._id, self.user.id, score)

    async def _login(self):
        cfg = website.config("client.cfg")["user"]
        name = cfg["name"]
        res = await self.net.login(name, cfg["password"])
        self.user = User(1 if res is None else res, name)
        self.guiapp.call(lambda: self.guiapp.window["settings"].show())

def main(addr: str):
    print("Client")
    client = Client(addr)
    client.main()

if __name__ == "__main__":
    Interface.main_thread()
    main("127.0.0.1")
    Interface.stop()
