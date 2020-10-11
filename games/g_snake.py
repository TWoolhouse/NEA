from game import Game, engine
import random

SCALE = 20

class Snake(engine.component.Script):
    def __init__(self):
        super().__init__()
        self.head = 0
        self.children = []
        self.delta = engine.core.DeltaTime()
        self.move_speed = 500

    def initialize(self) -> bool:
        self.time = 0
        self.modifier = 1
        self.dir = engine.Vector(-1, 0)
        return True

    def update(self):
        timestep = 0.05 / self.modifier
        self.keypress()
        self.collision()
        self.time += self.delta.value
        while self.time > timestep:
            self.time -= timestep
            self.move()

    def move(self):
        tail = self.children[self.head]
        self.head = (self.head - 1) % len(self.children)
        head = self.children[self.head]
        head.transform.position = tail.transform.position + self.dir * SCALE

    def keypress(self):
        if engine.input.key(engine.input.Key.W):
            self.dir = engine.Vector(0, -1)
        elif engine.input.key(engine.input.Key.S):
            self.dir = engine.Vector(0, 1)
        elif engine.input.key(engine.input.Key.A):
            self.dir = engine.Vector(-1, 0)
        elif engine.input.key(engine.input.Key.D):
            self.dir = engine.Vector(1, 0)

    def collision(self):
        head = self.children[self.head]
        if head.collider.collided():
            food = next(iter(head.collider.collisions))
            food.Get(Food).move()
            new = create_body(self._entity, engine.component.Transform(head.transform.position * 1))
            self.children.insert(self.head, new)
            self.move()
            self.modifier = 1 + len(self.children) * 0.05

class Food(engine.ecs.Component):

    def initialize(self):
        self.transform = self.Get(engine.component.Transform)
        self.move()
        return True

    def move(self):
        self.transform.position = engine.Vector(random.randrange(1, Game.width // SCALE), random.randrange(1, Game.height // SCALE)) * SCALE

class Body(engine.ecs.Component):

    def initialize(self):
        self.transform = self.Get(engine.component.Transform)
        self.collider = self.Get(engine.component.Collider)
        return True

def create_body(parent: engine.ecs.Entity, transform: engine.component.Transform):
    body = Body()
    engine.ecs.Instantiate( # Body Segments
        body,
        engine.component.Collider(engine.physics.collider.Point),
        engine.component.Render(engine.render.Polygon.Quad(0.9, 0.9)),
        parent=parent,
        transform=transform
    )
    return body

class Collision(engine.ecs.System):

    def update(self):
        for c in self.components(engine.component.Collider):
            c.collisions.clear()
        snakes = {s.children[s.head].collider for s in self.components(Snake)}
        for food, collider in self.components(Food, engine.component.Collider):
            for snake in snakes:
                if engine.physics.collider.detect(collider, snake):
                    collider.collisions.add(snake)
                    snake.collisions.add(collider)

class Application(Game):

    def initialize(self):
        # # REMOVE GLOBAL COLLISION - TEMPORARY FIX
        # index = None
        # for i, s in enumerate(engine.ecs.World.active()._systems):
        #     if isinstance(s, engine.ecs.systems.Collider):
        #         index = i
        #         break
        # engine.ecs.World.active()._systems.pop(index)
        engine.ecs.World.active()._systems.insert(1, Collision())

        engine.ecs.Instantiate( # FPS Counter
            engine.component.FPSCounter(10),
            engine.component.Render(engine.render.Text("FPS"), True),
            transform=engine.component.Transform(engine.Vector(Game.width - 20, 10))
        )

        snake_comp = Snake()
        snake = engine.ecs.Instantiate( # Snake
            snake_comp,
            transform=engine.component.Transform(scale=engine.Vector(SCALE, SCALE))
        )

        SIZE = 3
        for pos in range(SIZE):
            snake_comp.children.append(create_body(snake, engine.component.Transform(engine.Vector(Game.width // 2 + SCALE * pos, Game.height // 2))))

        FOOD = 1
        for iterations in range(FOOD):
            engine.ecs.Instantiate( # Food
                Food(),
                engine.component.Collider(engine.physics.collider.Point),
                engine.component.Render(engine.render.Polygon.Quad(SCALE * 0.9, SCALE * 0.9)),
            )

main = Application