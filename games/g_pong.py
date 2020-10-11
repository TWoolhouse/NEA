from game import Game, engine
import random

import neural
import pickle
from path import PATH

class Paddle(engine.component.Script):

    SIZE = engine.Vector(20, 100)
    QUAD = engine.render.Polygon.Quad(*SIZE)
    _CLAMPS = engine.Vector(0, SIZE[1] // 2 + 1), engine.Vector(Game.width, Game.height-(SIZE[1] // 2 + 1))
    SPEED = 500

    def __init__(self, side: int):
        self.side = side
        self._move_up = False
        self._move_down = False

    def initialize(self):
        super().initialize()
        self.transform = self.Get(engine.component.Transform)

    def update(self):
        ms = engine.Vector(0, self.SPEED * engine.core.DeltaTime.ph())
        if self._move_up:
            self._move_up = False
            self.transform.position -= ms
        if self._move_down:
            self._move_down = False
            self.transform.position += ms
        self.transform.position = self.transform.position.clamp(*self._CLAMPS)

    def move_up(self):
        self._move_up = True
    def move_down(self):
        self._move_down = True

class PaddlePlayer(engine.component.Script):

    def __init__(self, key_up: engine.input.Key, key_dn: engine.input.Key):
        self.key_up, self.key_dn = key_up, key_dn

    def initialize(self):
        super().initialize()
        self.paddle = self.Get(Paddle)

    def update(self):
        if engine.input.key(self.key_up):
            self.paddle.move_up()
        if engine.input.key(self.key_dn):
            self.paddle.move_down()

class PaddleAI(engine.component.Script):

    def __init__(self, ball, score):
        self.ball = ball
        self.score = score
        self.network = neural.Network(neural.layout.FeedForward(6, 2, *[15]*25))

    def initialize(self):
        super().initialize()
        self.paddle = self.Get(Paddle)
        self._clamp = (self.paddle._CLAMPS[0][1], self.paddle._CLAMPS[1][1])

        self._load_net()
        self._aglo = neural.algorithm.Genetic(self.network)
        self.network = next(self._aglo.train(10, 2, 0.9))

        self._value = 0
        self.count = 0

    def terminate(self):
        self._save_net()

    def update(self):
        data = [
            self.paddle.side,
            neural.maths.constrain(self.paddle.transform.position[1], *self._clamp),
            neural.maths.constrain(self.ball.transform.position[0], 0, Game.width),
            neural.maths.constrain(self.ball.transform.position[1], 0, Game.height),
            neural.maths.constrain(self.ball.velocity[0], 0, self.ball.SPEED),
            neural.maths.constrain(self.ball.velocity[1], 0, self.ball.SPEED),
        ]

        out = self.network.input(*data)
        if out[0] > out[1]:
            self.paddle.move_up()
        else:
            self.paddle.move_down()

        # TRAINING
        if self.ball.speed == 0:
            engine.app().event(engine.event.KeyPress(engine.input.Key.SPACE))

    def _load_net(self):
        try:
            with open(PATH+f"games/pong/{engine.app().program.game.id}.net", "rb") as file:
                self.network = pickle.load(file)
        except FileNotFoundError:
            pass
    def _save_net(self):
        with open(PATH+f"games/pong/{engine.app().program.game.id}.net", "wb") as file:
            pickle.dump(self.network, file)

    def event(self, event: engine.event.KeyPress):
        if event.dispatch(engine.event.KeyPress) and event.key is engine.input.Key.COLON:
            try:
                if self.count >= 5:
                    self._aglo.fitness(self._value)
                    self.network = next(self._aglo._iter)
                else:
                    self.count += 1
                    self._value += self.score.value
            except StopIteration:
                self.network = self._aglo.merge()
                engine.app().event(engine.event.KeyPress(engine.input.Key.ESCAPE))

class Ball(engine.component.Script):

    RADIUS = 25
    SPEED = 500
    RATE = 0.1
    RESOLUTION = 22.5

    def __init__(self, scores):
        self.velocity = engine.Vector(0, 0)
        self.speed = 1
        self.scores = scores

    def initialize(self):
        super().initialize()
        self.transform = self.Get(engine.component.Transform)
        self.collider = self.Get(engine.component.Collider)
        self.prev = None
        self.reset()

    def reset(self, side: int=None):
        self.transform.position = engine.Vector(Game.width, Game.height) // 2
        side = side if isinstance(side, int) else random.randint(0, 1)
        # theta = random.randint(7, 30) * (random.randint(0, 1) * 2 - 1)
        theta = 0
        self.velocity = engine.Vector(side * 2 - 1, 0).rotate(theta) * self.SPEED
        self.speed = 0

    def event_start(self, event):
        if event.dispatch(engine.event.KeyPress) and event.key is engine.input.Key.SPACE and self.speed == 0:
            engine.app().event(engine.event.KeyPress(engine.input.Key.COLON))
            self.start()
    def start(self):
        self.scores["tally"].value = 0
        self.speed = 1

    def collided(self):
        if self.collider.collision:
            if self.prev is None:
                collider = next(iter(self.collider.collision))
                self.prev = collider
                self.speed += self.RATE
                self.scores["tally"].value += 1
                if collider.Get(Paddle).side: # Right
                    self.velocity = engine.Vector(-abs(self.velocity[0]), self.velocity[1])
                else:
                    self.velocity = engine.Vector(abs(self.velocity[0]), self.velocity[1])
        else:
            self.prev = None

    def update(self):
        self.collided()

        self.transform.position += self.velocity * self.speed * engine.core.DeltaTime.ph()
        # Keep the ball within the top and bottom
        if self.transform.position[1] < Ball.RADIUS:
            self.velocity = engine.Vector(self.velocity[0], abs(self.velocity[1]))
        elif self.transform.position[1] > Game.height-Ball.RADIUS:
            self.velocity = engine.Vector(self.velocity[0], -abs(self.velocity[1]))

        # Reset the ball once of the sides
        if self.transform.position[0] < -Ball.RADIUS:
            side = 1
            self.scores["right"].value += 1
            self.reset(side)
        elif self.transform.position[0] > Game.width + Ball.RADIUS:
            side = 0
            self.scores["left"].value += 1
            self.reset(side)

class Score(engine.ecs.Component):

    def __init__(self, value):
        self.value = value

    def initialize(self):
        text = self.Get(engine.component.Render)
        if not isinstance(text.primative(), engine.render.Text) and text._vcache:
            raise TypeError("YOUR MOTHER")
        self.text = text

class ScoreManager(engine.ecs.System):

    def update(self, app: engine.core.Application):
        for component in self.components(Score):
            component.text.primative().text = component.value

class Application(Game):

    def initialize(self):
        app = engine.app()
        engine.instantiate(engine.component.Event(self.close, "WINDOW"))

        app.world.add_system(ScoreManager(), "RENDER")
        app.setting.collision().update({
            0: {1,},
        })

        scores = {
            "tally": Score(0),
            "left": Score(0),
            "right": Score(0)
        }

        engine.instantiate( # Ball
            (ball := Ball(scores)),
            engine.component.Event(ball.event_start), # Change collider to Circle once implemented
            engine.component.Collider(engine.physics.collider.Rectangle, engine.component.Transform(scl=engine.Vector(Ball.RADIUS, Ball.RADIUS)), 0),
            engine.component.Render(engine.render.Polygon.Circle(Ball.RADIUS, res=Ball.RESOLUTION)),
            transform=engine.component.Transform(engine.Vector(Game.width, Game.height) // 2)
        )

        score_parent = engine.instantiate(
            transform=engine.component.Transform(engine.Vector(Game.width // 2, Game.height // 10))
        )

        engine.instantiate(
            scores["tally"],
            engine.component.Render(engine.render.Text("T"), True),
            parent=score_parent,
            transform=engine.component.Transform(engine.Vector(0, 10))
        )

        engine.instantiate(
            scores["left"],
            engine.component.Render(engine.render.Text("L"), True),
            parent=score_parent,
            transform=engine.component.Transform(engine.Vector(-10, 0))
        )

        engine.instantiate(
            scores["right"],
            engine.component.Render(engine.render.Text("R"), True),
            parent=score_parent,
            transform=engine.component.Transform(engine.Vector(10, 0))
        )

        engine.instantiate( # Left Paddle
            Paddle(0),
            # (ai := PaddleAI(ball, scores["tally"])),
            # engine.component.Event(ai.event),
            PaddlePlayer(engine.input.Key.W, engine.input.Key.S),
            engine.component.Collider(engine.physics.collider.Rectangle, engine.component.Transform(scl=Paddle.SIZE), 1),
            engine.component.Render(Paddle.QUAD),
            transform=engine.component.Transform(engine.Vector(Paddle.SIZE[0], Game.height // 2))
        )

        engine.instantiate( # Right Paddle
            Paddle(1),
            # (ai := PaddleAI(ball, scores["tally"])),
            # engine.component.Event(ai.event),
            PaddlePlayer(engine.input.Key.UP, engine.input.Key.DOWN),
            engine.component.Collider(engine.physics.collider.Rectangle, engine.component.Transform(scl=Paddle.SIZE), 1),
            engine.component.Render(Paddle.QUAD),
            transform=engine.component.Transform(engine.Vector(Game.width - Paddle.SIZE[0], Game.height // 2))
        )

    def close(self, event: engine.event.KeyPress):
        if event.dispatch(engine.event.KeyPress) and event.key is engine.input.Key.ESCAPE:
            engine.app().event(engine.event.WindowClose())

main = Application()