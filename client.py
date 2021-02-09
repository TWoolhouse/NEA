import gui
import enum
import game
import node
import asyio
import loader
import caching
import functools
from interface import Interface
from typing import Callable, Any

class Requests(node.Client):
    def __init__(self, addr: str, port: int):
        super().__init__(addr, port)

    @caching.cache(1, 5)
    async def download(self, name: str):
        print("Download:", name)
        self.send(name, "GAME")
        data = await self.recv("GAME")
        if data and data[0].data:
            loader.write(data[0].data)
            return True
        return False

    @caching.cache(1, 5)
    async def retrieve_list(self):
        print("Retrieve List")
        self.send(b"", "GLIST")
        return [i.data for i in await self.recv(node.Tag("GLIST"), wait=(await self.recv("GLIST"))[0].data)]


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
        self.add(gui.tk.Button(self, text="Settings", command=lambda: self.show_page("settings")), row=3, column=1)

class PageGame(AppPage):
    def setup(self):
        self.add(gui.tk.Label(self, text="Games"), row=1, column=1, pady=10)
        self.add(gui.tk.Button(self, text="Current: None", command=self.play_game), "current", row=2, column=1, pady=15)
        self.add(gui.tk.Button(self, text="Return", command=lambda: self.show_page("home")), row=99, column=1, pady=15)
        self.edit("current", "state", "disabled")

    def show(self):
        Interface.schedule(self.app.client._retrieve_list())

    def update_listing(self):
        for name in tuple(self.widgets.keys()):
            if name.startswith("g_"):
                self.remove(name)

        for row, name in enumerate(sorted(self.app.client.games.names), start=3):
            self.add(gui.tk.Button(self, text=name.title(), command=gui.cmd(self.app.window["load_game"].load, name)), f"g_{name}", row=row, column=1, pady=2)

    def play_game(self):
        self.edit("current", "state", "disabled")
        self.edit("current", "text", "Running...")
        Interface.schedule(self.app.client._play_game())
        for name in tuple(self.widgets.keys()):
            if name.startswith("g_"):
                self.edit(name, "state", "disabled")

    def return_game(self):
        self.edit("current", "state", "normal")
        self.edit("current", "text", f"Current: {self.app.client.games.active}")
        for name in tuple(self.widgets.keys()):
            if name.startswith("g_"):
                self.edit(name, "state", "normal")

class PageLoadGame(AppPage):
    def setup(self):
        self.game_name = "None"
        self.add(gui.tk.Label(self, text="GAME NAME"), "game_name", row=1, column=1, pady=10)
        self.add(gui.tk.Button(self, text="Download", command=self.load_game), "download", row=2, column=1, pady=5)
        self.add(gui.tk.Button(self, text="Return", command=lambda: self.show_page("games")), row=99, column=1, pady=15)

    def load(self, name: str):
        self.edit("game_name", "text", name.title())
        self.game_name = name
        if not self.app.client._active.is_set():
            self.show_page(self.name)

    def show(self):
        self.edit("download", "state", "normal")
        self.edit("download", "text", "download")

    def load_game(self):
        self.parent["games"].edit("current", "state", "disabled")
        self.edit("download", "state", "disabled")
        self.edit("download", "text", "download...")
        print("Load Game:", self.game_name)
        Interface.schedule(self.app.client._load_game(self.game_name))

class PageSetting(AppPage):
    def setup(self):
        self.add(gui.tk.Label(self, text="Settings"), row=1, column=1, pady=15)
        self.add(gui.tk.Label(self, text="None"), "server", row=2, column=1)
        self.add(gui.tk.Button(self, text="Return", command=lambda: self.show_page("home")), row=99, column=1)

    def show(self):
        self.edit("server", "text", "Server: " + (self.app.client.net.addr if self.app.client.net else "Disconnected"))

class Client:
    def __init__(self, addr: str):
        self.guiapp = GuiApplication(self)
        self.net = Requests(addr, 609)
        self.games = loader.GameSet()
        self.games.names.add("dino")

        self._active = asyio.Nevent()

    def main(self):
        Interface.schedule(self.net.open())
        try:
            self.guiapp.main()
        finally:
            Interface.schedule(self.net.close())

    @caching.cache(1, 5)
    async def _retrieve_list(self) :
        names = await self.net.retrieve_list()
        self.games.names.clear()
        self.games.names.update(names)
        self.guiapp.call(self.guiapp.window["games"].update_listing)

    async def _load_game(self, name):
        if await self.net.download(name) and self.games.reload():
            self.games.active = name
        self.guiapp.call(self.guiapp.window["games"].edit, "current", "text", f"Current: {self.games.active}")
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
        await self.guiapp.acall(game.run, self.games.get().main)
        print("Game Over")
        self._active.clear()
        self.guiapp.call(self.guiapp.window["games"].return_game)

def main(addr: str):
    print("Client")
    client = Client(addr)
    client.main()

if __name__ == "__main__":
    Interface.main_thread()
    main("127.0.0.1")
    Interface.stop()
