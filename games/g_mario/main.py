from game import Game, engine

class PhysBody(engine.ecs.Component):
    def __init__(self):
        self.acceleration = engine.Vector(0, 0)
        self.velocity = engine.Vector(0, 0)

        self.ground = False
        self.drag = 1
        self.gravity = 1000
        self.mass = 1

    def initialize(self):
        self.transform = self.Get(engine.component.Transform)
        self.collider = self.Get(engine.component.Collider)
        return True

    def force(self, force: engine.Vector):
        self.acceleration += force / self.mass

class SysPhysBody(engine.ecs.System):
    def __init__(self):
        self.delta = engine.core.DeltaTime()

    def update(self):
        dt = 0.0016
        for component in self.components(PhysBody):
            component.transform.position += (component.velocity * dt) + (component.acceleration * (dt ** 2) * 0.5)
            component.velocity += component.acceleration * dt
            # component.velocity -= component.velocity * component.drag * self.delta.value
            # print(component.acceleration, component.velocity, component.transform.position)
            component.acceleration = engine.Vector(0, component.gravity)

class Player(engine.component.Script):
    def __init__(self):
        super().__init__()

    def initialize(self):
        self.transform = self.Get(engine.component.Transform)
        self.phys = self.Get(PhysBody)
        return True

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

class Collision(engine.ecs.System):
    def update(self):
        components = {c for c in self.components(engine.component.Collider) if c.Check(Player) is None}
        for body in self.components(PhysBody):
            body.collider.collisions.clear()
            for other in components:
                if engine.physics.collider.detect(body.collider, other):
                    body.collider.collisions.add(other)

class LandOnFloor(engine.ecs.System):
    def update(self):
        for phys in self.components(PhysBody):
            phys.ground = False
            if phys.collider.collided():
                for other in phys.collider.collisions:
                    if plat := other.Check(Platform):
                        phys.transform.position += engine.Vector(0, (other.transform.position_global[1] - phys.transform.position_global[1]) - ((other.transform.scale_global[1]) + (phys.collider.transform.scale_global[1])) / 2)
                        phys.velocity = engine.Vector(phys.velocity[0], 0)
                        phys.ground = True
                        break

class Application(Game):

    def initialize(self):
        engine.ecs.World.active()._systems.insert(1, SysPhysBody())
        engine.ecs.World.active()._systems.insert(2, Collision())
        engine.ecs.World.active()._systems.insert(3, LandOnFloor())

        engine.ecs.Instantiate( # FPS Counter
            engine.component.FPSCounter(10),
            engine.component.Render(engine.render.Text("FPS"), True),
            transform=engine.component.Transform(engine.Vector(Game.width - 20, 10))
        )

        engine.ecs.Instantiate( # Player
            Player(),
            PhysBody(),
            engine.component.Collider(engine.physics.collider.Rectangle, scale=engine.Vector(50, 50)),
            engine.component.Render(engine.render.Polygon.Quad(50, 50)),
            transform=engine.component.Transform(engine.Vector(Game.width // 8, 3 * Game.height // 4))
        )

        engine.ecs.Instantiate( # Platform
            Platform(),
            engine.component.Collider(engine.physics.collider.Rectangle, scale=engine.Vector(Game.width - 10, 20)),
            engine.component.Render(engine.render.Polygon.Quad(Game.width - 50, 20)),
            transform=engine.component.Transform(engine.Vector(Game.width // 2, Game.height - 50))
        )

main = Application