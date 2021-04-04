from game import Game, engine

class PhysBody(engine.ecs.Component):

    def __init__(self, mass: float=1):
        self.drag = 0.995
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

class Player(engine.component.Script):
    def __init__(self):
        super().__init__()

    def initialize(self):
        super().initialize()
        self.transform = self.Get(engine.component.Transform)
        self.phys = self.Get(PhysBody)

    def update(self):
        self.keypress()

    # def collision(self):
    #     if self.collider

    def keypress(self):
        force = 200
        if engine.input.key(engine.input.Key.D):
            self.phys.force(engine.Vector(force, 0))
        if engine.input.key(engine.input.Key.A):
            self.phys.force(engine.Vector(-force, 0))
        if engine.input.key(engine.input.Key.W) and self.phys.ground:
            print("JUMP", engine.core.DeltaTime().value)
            self.phys.force(engine.Vector(0, -force*2000))
        # if engine.input.key(engine.input.Key.S):
        #     self.phys.force(engine.Vector(0, force))

class Platform(engine.ecs.Component):
    def initialize(self):
        self.collider = self.Get(engine.component.Collider)
        return True

class Application(Game):

    def initialize(self):
        app = engine.app()
        engine.instantiate(engine.component.Event(self.close_event, "WINDOW"), id=False)

        app.window._master.title(f"Pyrio")
        app.world.system(engine.ecs.systems.Render, True)
        app.world.add_system(PhysBodySystem(), "PHYSICS")
        app.world.add_system(engine.ecs.systems.FPS(50), "POST")
        # engine.ecs.World.active()._systems.insert(2, Collision())
        # engine.ecs.World.active()._systems.insert(3, LandOnFloor())

        engine.instantiate( # FPS Counter
            engine.component.FPS(),
            engine.component.Render(engine.render.Text("FPS"), True),
            transform=engine.component.Transform(engine.Vector(Game.width - 20, 10))
        )

        engine.instantiate( # Player
            Player(),
            PhysBody(),
            engine.component.Collider(engine.physics.collider.Rectangle, engine.component.Transform(scl=engine.Vector(50, 50))),
            engine.component.Render(engine.render.Polygon.Quad(50, 50)),
            transform=engine.component.Transform(engine.Vector(Game.width // 8, 3 * Game.height // 4))
        )

        # engine.ecs.Instantiate( # Platform
        #     Platform(),
        #     engine.component.Collider(engine.physics.collider.Rectangle, scale=engine.Vector(Game.width - 10, 20)),
        #     engine.component.Render(engine.render.Polygon.Quad(Game.width - 50, 20)),
        #     transform=engine.component.Transform(engine.Vector(Game.width // 2, Game.height - 50))
        # )

    def close_event(self, event: engine.event.KeyPress):
        if event.dispatch(engine.event.KeyPress) and event.key is engine.input.Key.ESCAPE:
            engine.app().event(engine.event.WindowClose())

main = Application()
