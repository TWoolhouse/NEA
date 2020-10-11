from collections import deque
import enum
import random
from game import Game, engine

import neural
import pickle
from path import PATH

# AI
ITERATIONS = 7
RENDER = True
# AI

FLOOR = Game.height // 2 + Game.height // 4

class StateManager(engine.component.Script):

    @enum.unique
    class GameState(enum.IntEnum):
        NONE = 0
        RUN = 1
        HIT = 2
        PAUSE = 3
        UNPAUSE = 4

    def __init__(self):
        self.state = self.GameState.NONE
        self.score = 0

    def initialize(self):
        super().initialize()
        self.obstacle = self.Get(ObstacleManager)

        self._text_score = engine.render.Text(0)
        engine.instantiate(
            engine.component.Render(self._text_score, True),
            parent=self.entity,
            transform=engine.component.Transform(engine.Vector(Game.width - 20, 32))
        )
        self._text_high = engine.render.Text(0)
        engine.instantiate(
            engine.component.Render(self._text_high, True),
            parent=self.entity,
            transform=engine.component.Transform(engine.Vector(Game.width - 20, 20))
        )

        self._text_id = engine.render.Text(engine.app().program.game.id)
        engine.instantiate(
            engine.component.Render(self._text_id, True),
            parent=self.entity,
            transform=engine.component.Transform(engine.Vector(Game.width - 20, 44))
        )

        self._text_net_out = engine.render.Text([0, 0, 0])
        engine.instantiate(
            engine.component.Render(self._text_net_out, True),
            parent=self.entity,
            transform=engine.component.Transform(engine.Vector(Game.width - 300, 50))
        )

        self._text_net = engine.render.Text("NET")
        engine.instantiate(
            engine.component.Render(self._text_net, True),
            parent=self.entity,
            transform=engine.component.Transform(engine.Vector(Game.width - 300, 70))
        )

        self.state = self.GameState.RUN

    def update(self):
        self.score += engine.core.DeltaTime.dt() * 20 * int(self.state is self.GameState.RUN)
        self._text_score.text = round(self.score)
        if self._text_score.text > self._text_high.text:
            self._text_high.text = self._text_score.text

        if self.state is self.GameState.HIT:
            self.obstacle.collide()
            self.state = self.GameState.PAUSE
        if self.state is self.GameState.UNPAUSE:
            self.reset()
            self.state = self.GameState.RUN

    def collide(self):
        if self.state is self.GameState.RUN:
            self.state = self.GameState.HIT

    def reset(self):
        self.obstacle.reset()
        self.score = 0

    def restart(self, event: engine.event.Event):
        if event.dispatch(engine.event.KeyPress) and event.key is engine.input.Key.R:
            if self.state is self.GameState.PAUSE:
                self.reset()
                self.state = self.GameState.UNPAUSE

class Obstacle(engine.ecs.Component):

    def initialize(self):
        self.transform = self.Get(engine.component.Transform)
        self.collider = self.Get(engine.component.Collider)

class ObstacleManager(engine.component.Script):

    LIMIT = 10
    SPEED = 400
    RATE = 0.01
    AREA = 8000
    WIDTH = (40, 160)

    _offset = -Game.width // 4
    _spawn = 2 * Game.width
    __range = Game.width // 4 + Game.width // 6

    def __init__(self):
        self.children = deque()
        self.vel = engine.Vector(-self.SPEED, 0)
        self.speed = 1
        self.dist = 0
        self.reset()
        self.add()

    def initialize(self):
        super().initialize()
        self.state = self.Get(StateManager)

    def collide(self):
        self.vel = engine.Vector(0, 0)

    def reset(self):
        self.vel = engine.Vector(-self.SPEED, 0)
        self.speed = 1
        self.dist = 0
        for i in range(len(self.children)):
            self.remove()

    def update(self):
        self.speed += self.RATE * engine.core.DeltaTime.dt()
        try:
            if self.children[0].transform.position[0] < self._offset: # If head is offscreen
                self.remove()

            if (len(self.children) < self.LIMIT) and (self.children[-1].transform.position[0] < self._spawn - self.dist):
                self.add()
        except IndexError:
            self.add()

        ms = self.vel * (engine.core.DeltaTime.ph() * self.speed)
        for child in self.children:
            child.transform.position += ms

    def remove(self):
        engine.app().world.destroy(self.children.popleft().entity)

    def add(self):
        self.dist = random.randint(self.__range, Game.width)
        obstacle = Obstacle()
        width = random.randint(*self.WIDTH)
        dim = engine.Vector(width, self.AREA // width)
        engine.instantiate(
            obstacle,
            engine.component.Collider(engine.physics.collider.Rectangle, engine.component.Transform(scl=dim), 2),
            engine.component.Render(engine.render.Polygon.Quad(*dim)),
            transform=engine.component.Transform(engine.Vector(self._spawn, FLOOR - 2 - dim[1] // 2))
        )
        self.children.append(obstacle)

class PhysBody(engine.ecs.Component):

    def __init__(self, mass: float=1):
        self.mass = mass
        self.acceleration = engine.Vector(0, 0)
        self.velocity = engine.Vector(0, 0)

    def initialize(self):
        self.transform = self.Get(engine.component.Transform)

    def force(self, force: engine.Vector):
        self.acceleration += force / self.mass

class PhysBodySystem(engine.ecs.System):

    GRAVITY = engine.Vector(0, 9.81) * 100

    def update(self, app: engine.core.Application):
        dt = engine.core.DeltaTime.ph()
        for component in self.components(PhysBody):
            adt = component.acceleration * dt
            component.transform.position += component.velocity * dt + 0.5 * adt * dt
            component.velocity += adt
            component.acceleration = self.GRAVITY

class PlayerController(engine.component.Script):

    def __init__(self, manager: StateManager):
        self._jump = False
        self._fall = False
        self.floor = False
        self.manager = manager

    def initialize(self):
        super().initialize()
        self.body = self.Get(PhysBody)
        self.transform = self.Get(engine.component.Transform)
        self.collider = self.Get(engine.component.Collider)

    def update(self):
        collisions = {l for c in self.collider.collision for l in c.layers}
        if 1 in collisions:
            self.floor = True
        else:
            self.floor = False

        if 2 in collisions:
            self.manager.collide()
            try:
                self.Get(PlayerControllerAI).fail()
            except engine.error.ecs.GetComponentError:
                pass

        if self._jump:
            self._jump = False
            if self.floor:
                self.body.force(engine.Vector(0, -5000))

        if self._fall:
            self._fall = False
            if not self.floor:
                self.body.force(engine.Vector(0, 250))

        if self.floor:
            self.transform.position = engine.Vector(self.transform.position[0], FLOOR - 50)
            self.body.velocity = engine.Vector(self.body.velocity[0], 0)

    def jump(self):
        self._jump = True

    def fall(self):
        self._fall = True

class PlayerControllerInput(engine.component.Script):
    def __init__(self):
        self.key_up, self.key_dn = engine.input.Key.W, engine.input.Key.S

    def initialize(self):
        super().initialize()
        self.controller = self.Get(PlayerController)

    def update(self):
        if engine.input.key(self.key_up):
            self.controller.jump()
        if engine.input.key(self.key_dn):
            self.controller.fall()

class PlayerControllerAI(engine.component.Script):

    # HEIGHT = 
    __height = (ObstacleManager.AREA // ObstacleManager.WIDTH[1], ObstacleManager.AREA // ObstacleManager.WIDTH[0])

    def __init__(self, manager: StateManager):
        self.manager = manager
        # Inputs:
        # Obstacles - Value
        # Player - Y, YVel
        # Obs_Closest - X, Width, Height
        # Obs_Next - X, Width, Height
        # Obs_3 - X, Width, Height
        self.network = neural.Network(neural.layout.FeedForward(1, 3, *[15]*15))
        # Nothing, Jump, Fall

    def initialize(self):
        super().initialize()
        self.controller = self.Get(PlayerController)
        self._load_net()
        # self._aglo = neural.algorithm.Genetic(self.network)
        # self.network = next(self._aglo.train(ITERATIONS, 2))

    def terminate(self):
        self._save_net()

    def _load_net(self):
        try:
            with open(PATH+f"games/dino/fall.net", "rb") as file:
                self.network = pickle.load(file)
        except FileNotFoundError:
            pass
    def _save_net(self):
        # with open(PATH+f"games/dino/{engine.app().program.game.id}.new.net", "wb") as file:
        #     pickle.dump(self.network, file)
        pass

    def update(self):
        # data = [
        #     neural.maths.constrain(len(self.manager.obstacle.children), 0, ObstacleManager.LIMIT),
        #     neural.maths.constrain(self.controller.transform.position[1], 0, Game.height),
        #     # self.controller.body.velocity[1],
        # ]
        # for i in range(3):
        #     try:
        #         child = self.manager.obstacle.children[0]
        #     except IndexError:
        #         data.extend((1, 0, 0))
        #         continue
        #     data.append(neural.maths.constrain(child.transform.position[0], ObstacleManager._offset, ObstacleManager._spawn))
        #     sx, sy = child.collider.transform.scale
        #     data.append(neural.maths.constrain(sx, ObstacleManager.WIDTH[0], ObstacleManager.WIDTH[1]))
        #     data.append(neural.maths.constrain(sy, self.__height[0], self.__height[1]))
        data = []
        try:
            child = self.manager.obstacle.children[0]
            data.append(neural.maths.constrain(child.transform.position[0], ObstacleManager._offset, ObstacleManager._spawn))
        except IndexError:
            data.append(1)
        out = self.network.input(*data)
        self.manager._text_net_out.text = out
        com = out.index(max(out))
        self.manager._text_net.text = com
        if com == 1:
            self.controller.jump()
        elif com == 2:
            self.controller.fall()

    def fail(self):
        if self.manager.state is self.manager.GameState.PAUSE:
            # try:
            #     title = engine.app().window._master.title().split("-")
            #     iteration = int(title[-1])
            #     print(f"ID<{engine.app().program.game.id}> {iteration}: {int(self.manager.score)}")
            #     new_title = "-".join(title[:-1]) + f"-{iteration+1}"
            #     self._aglo.fitness(self.manager.score)
            #     self.network = next(self._aglo._iter)
            #     engine.app().window._master.title(new_title)
            # except StopIteration:
            #     self.network = self._aglo.merge()
            #     engine.app().event(engine.event.KeyPress(engine.input.Key.ESCAPE))
            engine.app().event(engine.event.KeyPress(engine.input.Key.R))

class Application(Game):

    def initialize(self):
        app = engine.app()
        engine.instantiate(engine.component.Event(self.close_event, "WINDOW"), id=False)

        app.window._master.title(f"Dino-{app.program.game.id}-0")
        app.world.system(engine.ecs.systems.Render, RENDER)
        app.world.add_system(PhysBodySystem(), "PHYSICS")

        app.setting.collision().update({
            0: {1, 2}, # Player
        })

        manager = StateManager()
        engine.instantiate(
            manager,
            ObstacleManager(),
            engine.component.Event(manager.restart)
        )

        engine.instantiate( # Player
            # PlayerControllerInput(),
            PlayerControllerAI(manager),
            PlayerController(manager),
            PhysBody(0.06),
            engine.component.Collider(engine.physics.collider.Rectangle, engine.component.Transform(scl=engine.Vector(50, 100)), 0),
            engine.component.Render(engine.render.Polygon.Quad(50, 100)),
            transform=engine.component.Transform(engine.Vector(Game.width // 16, Game.height // 2))
        )

        engine.instantiate( # Floor
            engine.component.Collider(engine.physics.collider.Rectangle, engine.component.Transform(scl=engine.Vector(Game.width, 20)), 1),
            engine.component.Render(engine.render.Polygon.Quad(Game.width, 20)),
            transform=engine.component.Transform(engine.Vector(Game.width // 2, FLOOR + 10))
        )

    def close_event(self, event: engine.event.KeyPress):
        if event.dispatch(engine.event.KeyPress) and event.key is engine.input.Key.ESCAPE:
            engine.app().event(engine.event.WindowClose())

main = Application()