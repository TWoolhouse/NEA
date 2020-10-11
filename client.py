import enum
import network
import loader
import game
import gui

class Application:
    def __init__(self, client):
        self.client = client
        self.window = gui.Window("Game Client Menu")
        PageHome(self.window)
        PageGame(self.window, self)
        PageSetting(self.window, self)
        self.window.show_page("home")

    def main(self):
        if self.client.network.is_open():
            for page in self.window.pages:
                pass

class AppPage(gui.Page):
    def __init__(self, parent, app):
        self.app = app
        super().__init__(parent, "home")

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
        self.add(gui.tk.Button(self, text="Current: None", command=lambda: None), "current", row=2, column=1, pady=5)
        self.add(gui.tk.Button(self, text="Return", command=lambda: self.show_page("home")), row=99, column=1, pady=15)

    def update_list(self, games):
        self.client.update_list()

class PageSetting(AppPage):
    def setup(self):
        self.add(gui.tk.Label(self, text="Settings"), row=1, column=1, pady=15)
        self.add(gui.tk.Label(self, text="None"), "server", row=2, column=1)
        self.add(gui.tk.Button(self, text="Return", command=lambda: self.show_page("home")), row=99, column=1)

    def show(self):
        self.edit("server", "text", "Server: " + (self.app.client.network.conn_name() if self.app.client.network.is_open() else "Disconnected"))

class Client:
    def __init__(self, addr: str):

        # Module
        self.module = loader.Module()

        # Network Client
        self.network = network.Client(addr)

        # Window
        self.application = Application(self)

    def main(self):
        try:
            self.network.open()
        except network.node.CloseError:
            print("Connection Error")
        try:
            self.application.main()
        finally:
            self.network.close()

    def update_list(self):
        pass

    def request_game(self, index: int):
        if self.network.is_open():
            if self.network.game(self.module.names[index]) and self.module.reload():
                self.module._active = index
        else:
            self.application.

def main(addr: str):
    print("Client")
    client = Client(addr)
    client.main()

if __name__ == "__main__":
    main("127.0.0.1")