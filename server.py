import db
import node
import loader
import asyncio
import website
from interface import Interface

class SClient(node.SClient):

    async def open(self):
        await super().open()
        self.db: db.Database = self.server.database
        print("Connection:", self._node)

    async def dsptch_game(self, data: node.Data):
        print("Game Request:", data.data)
        if game := await self.db.game(data.data):
            print("Game File:", data.data, game[0])
            return self.send(loader.read_game(game[1]), "GAME", node.Tag(data.data))
        print("Game Not Found:", data.data)
        return self.send(False, "GAME", node.Tag(data.data))

    async def dsptch_glist(self, data: node.Data):
        print("Request Game List")
        glist = await self.db.game_list()
        self.send(len(glist), "GLIST")
        for element in glist:
            self.send(tuple(element), "GLIST")

    async def dsptch_ailist(self, data: node.Data):
        print("Request AI List", data.data)
        ailist = await self.db.ai_list(data.data)
        tag = node.Tag(data.data)
        self.send(len(ailist), "AILIST", tag)
        for element in ailist:
            self.send(tuple(element), "AILIST", tag)

    async def dsptch_ai(self, data: node.Data):
        print("AI Request:", data.data)
        if ai := await self.db.ai(data.data):
            _, filename = await self.db.ai_game(data.data)
            ai_data = loader.read_ai(filename, ai[1])
            return self.send(ai_data, "AI", node.Tag(data.data))
        return self.send(False, "AI", node.Tag(data.data))

    async def dsptch_database(node: 'node.DataInterface', data: node.Data):
        print("Database Request", data)

class CSStyle(website.Request):
    async def handle(self):
        self.client.header << website.Header("Content-Type", "text/css")
        self.client.header << website.Header("Cache-Control", "public, max-age=604800, immutable")
        await self.load_style("/".join(self.request[1:]))

    async def load_style(self, filename: str):
        data = await website.buffer.File(website.path+"resource/style/"+filename).compile()
        if data.startswith(b"# meta"):
            lines = data.splitlines(False)[1:]
            for index, fname in enumerate(lines, start=1):
                if fname:
                    if fname.startswith(b"# meta"):
                        self.client.buffer << b"\n".join(lines[index+1:])
                        break
                    await self.load_style(fname.decode())
        else:
            self.client.buffer << data

class Server(node.Server):
    # Get Database Referance
    database = db.Database()

    class WebRequest(website.Request):
        inst = None
        end = asyncio.Event()

        async def handle(self):
            print(f"{self.client.peer}:{self.client.port} /{'/'.join(self.request)}")
            await self.tree.traverse(self)

        def kill(self):
            if self.client.query.get("key") == "adminkill":
                self.kill_flag = True
                async def kill_timer():
                    await Interface.next(1)
                    self.end.set()
                Interface.schedule(kill_timer())
            self.client.buffer << website.buffer.Python(f"{website.path}web/page/kill.html", self)

        tree = website.Tree(
            (home := website.buffer.Python(f"{website.path}web/page/home.html")),
            home, home,
            kill=kill,
            style=CSStyle,
        )

    def __init__(self):
        self.WebRequest.inst = self
        self.web = website.Server(self.WebRequest, port=610)
        website.buffer.Buffer.cache_disable = True # DEBUG
        super().__init__("", 609, 10, False, SClient, echo=node.dispatch.echo)

    async def __aenter__(self):
        await self.database.__aenter__()
        await super().__aenter__()
        await self.web.__aenter__()
        return self
    async def __aexit__(self, *args):
        await self.web.__aexit__(*args)
        await super().__aexit__(*args)
        await self.database.__aexit__(*args)
        return

async def main(repopulate=False):
    print("Server")
    # Repopulate the Database
    if repopulate:
        Server.database.new()
        async with Server.database:
            await Server.database.repopulate()

    server = Server()
    #  Main Serving Loop
    async with server:
        await server.WebRequest.end.wait()

    Interface.stop()

if __name__ == "__main__":
    from interface import Interface
    Interface.schedule(main(repopulate=True))
    Interface.main()
