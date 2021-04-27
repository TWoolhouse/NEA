import enum
import time
import engine
import neural
import collections
import multiprocessing as mp
from interface import Interface

@enum.unique
class AI_State(enum.IntEnum):
    NONE = 0
    PLAYER = 1
    ACTIVE = 2
    TRAIN = 3

class GameApplication(engine.core.Program):

    width, height = 1280, 720
    AI: neural.Network = neural.Network(neural.layout.Layout((0,),(0,),[(0,(),neural.neuron.Neuron)]))
    AIState: AI_State = AI_State.NONE
    callback = lambda s: None

    def initialize(self, app: engine.core.Application):
        app.world.systems.add(engine.layer.Data(app.world.systems.type.PRE, engine.ecs.systems.FPS(10), False))
        app.world.systems.add(engine.layer.Data(app.world.systems.type.RENDER, engine.ecs.systems.Render()))
        app.world.systems.add(engine.layer.Data(app.world.systems.type.SCRIPT, engine.ecs.systems.Script()))
        app.world.systems.add(engine.layer.Data(app.world.systems.type.PHYSICS, engine.ecs.systems.Collider()))

    def database(self, score: int):
        if Interface.single():
            Interface.schedule(self.callback, int(score))

def run(game: GameApplication, nn: neural.Network, ai_state: AI_State):
    game.AIState = ai_state
    game.AI = nn
    app = engine.core.Application(game)
    engine.main(app)

def run_player(game: GameApplication):
    run(game, None, AI_State.PLAYER)

def run_ai(game: GameApplication, ai: neural.Network) -> mp.Process:
    proc = mp.Process(target=run, args=(game, ai, AI_State.ACTIVE))
    proc.start()
    return proc

def run_train_ai(game: GameApplication, ai: neural.Network, iterations: int):
    game.iterations = iterations
    run(game, ai, AI_State.TRAIN)
    return game.fitness

def __starmap(args):
    return run_train_ai(*args)

def run_train(game: GameApplication, algorithm: neural.algorithm.Genetic, iterations: int=3, simultaneous: int=None, timeout: int=60) -> neural.algorithm.Genetic:
    simultaneous = algorithm.population_size if simultaneous is None else simultaneous
    with mp.Pool(simultaneous) as pool:
        try:
            scores = pool.map_async(__starmap, ((game, n, iterations) for n in algorithm.population())).get(timeout)
        except mp.TimeoutError:
            return None
    collections.deque(map(algorithm.fitness, algorithm.population(), scores), maxlen=0)
    n, s = algorithm.merge(save=False)
    return s
