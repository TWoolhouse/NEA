import engine
import multiprocessing as mp
import time

class Game: # Subclass for each game

    width, height = 1280, 720

    def initialize(self):
        pass
    def terminate(self):
        pass

class Application(engine.core.Program):

    def __init__(self, game: Game):
        self.game = game

    def initialize(self, app: engine.core.Application):
        app.world.systems.add(engine.layer.Data(app.world.systems.type.PRE, engine.ecs.systems.FPS(10), False))
        app.world.systems.add(engine.layer.Data(app.world.systems.type.RENDER, engine.ecs.systems.Render()))
        app.world.systems.add(engine.layer.Data(app.world.systems.type.SCRIPT, engine.ecs.systems.Script()))
        app.world.systems.add(engine.layer.Data(app.world.systems.type.PHYSICS, engine.ecs.systems.Collider()))

        self.game.initialize()

    def terminate(self, app: engine.core.Application):
        self.game.terminate()

def run(game: Game, id: int=1):
    game.id = id
    app = engine.core.Application(Application(game))
    engine.main(app)

def proc_run(game: Game, procs: int=1, timeout: int=120):
    processes = []
    for pid in range(1, procs+1):
        process = mp.Process(target=run, args=(game, pid))
        process.start()
        time.sleep(0.1)
        processes.append(process)
    for p in processes:
        p.join(timeout)
        p.kill()