from game import engine, GameApplication
import enum
import neural
import random
from collections import deque
from interface import Interface

FLOOR = GameApplication.height // 2 + GameApplication.height // 4

class StateManager(engine.component.Script):

    @enum.unique
    class GameState(enum.IntEnum):
        NONE = 0
        RUN = 1
        HIT = 2
        PAUSE = 3

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
            transform=engine.component.Transform(engine.Vector(GameApplication.width - 20, 32))
        )
        self._text_high = engine.render.Text(0)
        engine.instantiate(
            engine.component.Render(self._text_high, True),
            parent=self.entity,
            transform=engine.component.Transform(engine.Vector(GameApplication.width - 20, 20))
        )

        if engine.app().program.AIState >= GameApplication.AIState.ACTIVE:
            self._text_net_out = engine.render.Text([0, 0, 0])
            engine.instantiate(
                engine.component.Render(self._text_net_out, True),
                parent=self.entity,
                transform=engine.component.Transform(engine.Vector(GameApplication.width - 300, 50))
            )

            self._text_net = engine.render.Text("NET")
            engine.instantiate(
                engine.component.Render(self._text_net, True),
                parent=self.entity,
                transform=engine.component.Transform(engine.Vector(GameApplication.width - 300, 70))
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

    def collide(self):
        if self.state is self.GameState.RUN and (self.score - engine.core.DeltaTime().dt() * 20) >= 1:
            self.state = self.GameState.HIT
            engine.app().program.database(self.score)

    def reset(self):
        self.obstacle.reset()
        self.score = 0

    def restart(self, event: engine.event.Event):
        if event.dispatch(engine.event.KeyPress) and event.key is engine.input.Key.R:
            if self.state is self.GameState.PAUSE:
                self.reset()
                self.state = self.GameState.RUN

@engine.ecs.require(engine.component.Collider)
class Obstacle(engine.ecs.Component):

    def __init__(self, width, height):
        self.width, self.height = width, height

    def initialize(self):
        self.transform = self.Get(engine.component.Transform)
        self.collider = self.Get(engine.component.Collider)

@engine.ecs.require(StateManager)
class ObstacleManager(engine.component.Script):

    LIMIT = 10
    SPEED = 400
    RATE = 0.01
    AREA = 8000
    WIDTH = (40, 160)
    HEIGHT = AREA // WIDTH[0]

    _offset = -GameApplication.width // 4
    _spawn = 2 * GameApplication.width
    __range = GameApplication.width // 4 + GameApplication.width // 6

    def __init__(self):
        self.children = deque()
        self.vel = engine.Vector(-self.SPEED, 0)
        self.speed = 1
        self.dist = 0

        self._colour_array = [(1,0,0), (1,.75,0), (0,1,0), (0,.5,.5), (0,0,1), (.5,0,.5)]
        self._colour_count = 0

    def initialize(self):
        super().initialize()
        self.state = self.Get(StateManager)
        self._colour_array = [engine.render.Colour(*c) for c in self._colour_array]

        self.reset()
        self.add()

    def collide(self):
        self.vel = engine.Vector(0, 0)

    def reset(self):
        self.vel = engine.Vector(-self.SPEED, 0)
        self.speed = 1
        self.dist = 0
        for i in range(len(self.children)):
            self.remove()
        self._colour_count = 0

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
        self.dist = random.randint(self.__range, GameApplication.width)
        width = random.randint(*self.WIDTH)
        dim = engine.Vector(width, self.AREA // width)
        obstacle = Obstacle(*dim)
        engine.instantiate(
            obstacle,
            engine.component.Collider(engine.physics.collider.Rectangle, engine.component.Transform(scl=dim), "Obstacle"),
            engine.component.Render(engine.render.Polygon.Quad(*dim, col=self._colour_array[self._colour_count % len(self._colour_array)])),
            transform=engine.component.Transform(engine.Vector(self._spawn, FLOOR - 2 - dim[1] // 2))
        )
        self.children.append(obstacle)
        self._colour_count += 1

engine.ecs.require(ObstacleManager)(StateManager)

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

@engine.ecs.require(PhysBody, engine.component.Collider)
class PlayerController(engine.component.Script):

    def __init__(self, manager: StateManager):
        self._jump = False
        self._fall = False
        self.floor = False
        self.manager = manager
        self.layers: engine.layer.Type = engine.app().setting.collision().layers

    def initialize(self):
        super().initialize()
        self.body = self.Get(PhysBody)
        self.transform = self.Get(engine.component.Transform)
        self.collider = self.Get(engine.component.Collider)

    def update(self):
        collisions = {l for c in self.collider.collision for l in c.layers}
        if self.layers["Enviroment"] in collisions:
            self.floor = True
        else:
            self.floor = False

        if self.layers["Obstacle"] in collisions:
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

@engine.ecs.require(PlayerController)
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

@engine.ecs.require(PlayerController)
class PlayerControllerAI(engine.component.Script):

    def __init__(self, manager: StateManager):
        self.manager = manager
        # Inputs:
        # i = range(2)
        # Obs[i] - X, Height
        self.network = Application.AI
        # Output: Fall, Jump

        self.iteration, self.score = 0, 0

    def initialize(self):
        super().initialize()
        self.controller = self.Get(PlayerController)
        self.network = engine.app().program.AI
        engine.app().window.title(f"Dinosaur - {self.iteration}")

    def terminate(self):
        app = engine.app()
        if app.program.AIState is not app.program.AIState.TRAIN:
            return
        if self.iteration < engine.app().program.iterations:
            engine.app().program.fitness = None
        else:
            engine.app().program.fitness = self.score / self.iteration

    def update(self):
        data = [1] * 2
        for i in range(2):
            try:
                child = self.manager.obstacle.children[i]
                data[i] = neural.maths.constrain(child.transform.position[i], ObstacleManager._offset, ObstacleManager._spawn)
            except IndexError:    pass
        out = self.network.feed(*data)
        self.manager._text_net_out.text = out
        self.network.result(out, self.controller.fall, self.controller.jump)
        self.manager._text_net.text = out.index(max(out))

    def fail(self):
        if self.manager.state is self.manager.GameState.PAUSE:
            app = engine.app()
            if app.program.AIState is not app.program.AIState.TRAIN:
                return app.event(engine.event.KeyPress(engine.input.Key.R))
            self.iteration += 1
            self.score += self.manager.score
            app.window.title(f"Dinosaur - {self.iteration}")
            if self.iteration >= app.program.iterations:
                return app.event(engine.event.KeyPress(engine.input.Key.ESCAPE))
            app.event(engine.event.KeyPress(engine.input.Key.R))

class Application(GameApplication):

    AI = neural.Network(neural.layout.FeedForward(
        (5, neural.neuron.Input),
        (2, neural.neuron.Output),
        *[(3, neural.neuron.Hidden)] * 1,
        *[(3, neural.neuron.Recurrent)] * 3,
        *[(3, neural.neuron.Hidden)] * 1,
    ))

    def initialize(self, app: engine.core.Application):
        super().initialize(app)
        engine.instantiate(engine.component.Event(self.close_event, "WINDOW"), id=False)

        app.window._master.title(f"Dinosaur")
        app.world.system(engine.ecs.systems.Render, True)
        app.world.add_system(PhysBodySystem(), "PHYSICS")
        app.world.add_system(engine.ecs.systems.FPS(), "POST")

        setting_collision = app.setting.collision()
        setting_collision.matrix.make(
            setting_collision.layers.set("Player", 10),
            setting_collision.layers.set("Enviroment", 11),
            setting_collision.layers.set("Obstacle", 12),
        )
        setting_collision.matrix.compile()

        setting_render = app.setting.render()
        setting_render.layers["Player"] = 110
        setting_render.compile()

        manager = StateManager()
        engine.instantiate(
            manager,
            ObstacleManager(),
            engine.component.Event(manager.restart)
        )

        engine.instantiate( # Player
            PlayerController(manager),
            PlayerControllerAI(manager) if self.AIState >= self.AIState.ACTIVE else PlayerControllerInput(),
            PhysBody(0.06),
            engine.component.Collider(engine.physics.collider.Rectangle, engine.component.Transform(scl=engine.Vector(50, 100)), "Player"),
            engine.component.Render(engine.render.Polygon.Quad(50, 100), layer="Player"),
            transform=engine.component.Transform(engine.Vector(GameApplication.width // 16, GameApplication.height // 2))
        )

        engine.instantiate( # Floor
            engine.component.Collider(engine.physics.collider.Rectangle, engine.component.Transform(scl=engine.Vector(GameApplication.width, 20)), "Enviroment"),
            engine.component.Render(engine.render.Polygon.Quad(GameApplication.width, 20)),
            transform=engine.component.Transform(engine.Vector(GameApplication.width // 2, FLOOR + 10))
        )

        engine.instantiate( # FPS
            engine.component.FPS(),
            engine.component.Render(engine.render.Text("FPS"), True),
            transform=engine.component.Transform(engine.Vector(GameApplication.width - 20, 8))
        )

    def close_event(self, event: engine.event.KeyPress):
        if event.dispatch(engine.event.KeyPress) and event.key is engine.input.Key.ESCAPE:
            engine.app().event(engine.event.WindowClose())

main = Application()
