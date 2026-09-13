from __future__ import annotations

import math
import random
import sys
from collections import deque

import pygame

from gravity_sim import Body, NBodySimulation

WIDTH, HEIGHT = 1100, 720
BACKGROUND = (10, 13, 22)
GRID = (26, 31, 44)
TEXT = (225, 230, 240)
MUTED = (150, 160, 180)


def default_system() -> list[Body]:
    """A stable-ish normalized star/planet/moon demo."""
    star = Body(0, 0, 0, 0, mass=1600, radius=13, color=(255, 205, 80), name="Star")

    r1 = 165.0
    v1 = math.sqrt(star.mass / r1)
    planet = Body(r1, 0, 0, v1, mass=7, radius=7, color=(80, 160, 255), name="Planet")

    r2 = 285.0
    v2 = math.sqrt(star.mass / r2)
    outer = Body(0, -r2, v2, 0, mass=14, radius=9, color=(225, 110, 90), name="Outer")

    moon_offset = 28.0
    moon_speed = math.sqrt(planet.mass / moon_offset)
    moon = Body(
        r1 + moon_offset,
        0,
        0,
        v1 + moon_speed,
        mass=0.07,
        radius=4,
        color=(210, 210, 220),
        name="Moon",
    )
    return [star, planet, outer, moon]


class GravityApp:
    def __init__(self) -> None:
        pygame.init()
        pygame.display.set_caption("2D Gravity Simulator")
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.RESIZABLE)
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("consolas", 18)
        self.small_font = pygame.font.SysFont("consolas", 15)

        self.sim = NBodySimulation(default_system(), softening=4.0)
        self.paused = False
        self.show_trails = True
        self.time_scale = 1.0
        self.zoom = 1.0
        self.camera_x = 0.0
        self.camera_y = 0.0
        self.trails: list[deque[tuple[float, float]]] = []
        self.drag_start: tuple[float, float] | None = None
        self.ensure_trails()

    def ensure_trails(self) -> None:
        while len(self.trails) < len(self.sim.bodies):
            self.trails.append(deque(maxlen=500))
        if len(self.trails) > len(self.sim.bodies):
            self.trails = self.trails[: len(self.sim.bodies)]

    def reset(self) -> None:
        self.sim = NBodySimulation(default_system(), softening=4.0)
        self.trails = []
        self.ensure_trails()
        self.time_scale = 1.0
        self.zoom = 1.0
        self.camera_x = self.camera_y = 0.0
        self.paused = False

    def world_to_screen(self, x: float, y: float) -> tuple[int, int]:
        w, h = self.screen.get_size()
        sx = (x - self.camera_x) * self.zoom + w / 2
        sy = (y - self.camera_y) * self.zoom + h / 2
        return int(sx), int(sy)

    def screen_to_world(self, sx: float, sy: float) -> tuple[float, float]:
        w, h = self.screen.get_size()
        x = (sx - w / 2) / self.zoom + self.camera_x
        y = (sy - h / 2) / self.zoom + self.camera_y
        return x, y

    def add_body(self, pos: tuple[int, int]) -> None:
        x, y = self.screen_to_world(*pos)
        angle = random.random() * math.tau
        speed = random.uniform(0.2, 1.1)
        mass = random.uniform(2.0, 12.0)
        color = random.choice(
            [(140, 220, 255), (255, 150, 120), (180, 255, 160), (225, 180, 255)]
        )
        self.sim.bodies.append(
            Body(
                x,
                y,
                math.cos(angle) * speed,
                math.sin(angle) * speed,
                mass=mass,
                radius=max(4.0, min(9.0, 3.5 + math.sqrt(mass))),
                color=color,
                name=f"Body {len(self.sim.bodies) + 1}",
            )
        )
        self.ensure_trails()

    def remove_nearest(self, pos: tuple[int, int]) -> None:
        if not self.sim.bodies:
            return
        x, y = self.screen_to_world(*pos)
        index = min(
            range(len(self.sim.bodies)),
            key=lambda i: (self.sim.bodies[i].x - x) ** 2 + (self.sim.bodies[i].y - y) ** 2,
        )
        del self.sim.bodies[index]
        del self.trails[index]

    def handle_event(self, event: pygame.event.Event) -> bool:
        if event.type == pygame.QUIT:
            return False
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_ESCAPE, pygame.K_q):
                return False
            if event.key == pygame.K_SPACE:
                self.paused = not self.paused
            elif event.key == pygame.K_r:
                self.reset()
            elif event.key == pygame.K_t:
                self.show_trails = not self.show_trails
            elif event.key in (pygame.K_EQUALS, pygame.K_PLUS, pygame.K_KP_PLUS):
                self.time_scale = min(16.0, self.time_scale * 2.0)
            elif event.key in (pygame.K_MINUS, pygame.K_KP_MINUS):
                self.time_scale = max(0.125, self.time_scale / 2.0)
        elif event.type == pygame.MOUSEWHEEL:
            factor = 1.12 ** event.y
            self.zoom = max(0.15, min(8.0, self.zoom * factor))
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                self.add_body(event.pos)
            elif event.button == 3:
                self.remove_nearest(event.pos)
            elif event.button == 2:
                self.drag_start = event.pos
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 2:
            self.drag_start = None
        elif event.type == pygame.MOUSEMOTION and self.drag_start is not None:
            dx = event.pos[0] - self.drag_start[0]
            dy = event.pos[1] - self.drag_start[1]
            self.camera_x -= dx / self.zoom
            self.camera_y -= dy / self.zoom
            self.drag_start = event.pos
        return True

    def update(self) -> None:
        if not self.paused:
            dt = 0.045 * self.time_scale
            substeps = max(1, int(math.ceil(self.time_scale)))
            sub_dt = dt / substeps
            for _ in range(substeps):
                self.sim.step(sub_dt)

        self.ensure_trails()
        for trail, body in zip(self.trails, self.sim.bodies):
            trail.append((body.x, body.y))

    def draw_grid(self) -> None:
        w, h = self.screen.get_size()
        spacing_world = 100.0
        spacing_px = spacing_world * self.zoom
        if spacing_px < 35:
            spacing_world *= math.ceil(35 / spacing_px)

        left, top = self.screen_to_world(0, 0)
        right, bottom = self.screen_to_world(w, h)
        start_x = math.floor(left / spacing_world) * spacing_world
        start_y = math.floor(top / spacing_world) * spacing_world

        x = start_x
        while x <= right:
            sx, _ = self.world_to_screen(x, 0)
            pygame.draw.line(self.screen, GRID, (sx, 0), (sx, h), 1)
            x += spacing_world

        y = start_y
        while y <= bottom:
            _, sy = self.world_to_screen(0, y)
            pygame.draw.line(self.screen, GRID, (0, sy), (w, sy), 1)
            y += spacing_world

    def draw(self) -> None:
        self.screen.fill(BACKGROUND)
        self.draw_grid()

        if self.show_trails:
            for trail, body in zip(self.trails, self.sim.bodies):
                if len(trail) >= 2:
                    points = [self.world_to_screen(x, y) for x, y in trail]
                    pygame.draw.lines(self.screen, body.color, False, points, 1)

        for body in self.sim.bodies:
            sx, sy = self.world_to_screen(body.x, body.y)
            radius = max(2, int(body.radius * min(self.zoom, 2.2)))
            pygame.draw.circle(self.screen, body.color, (sx, sy), radius)

        status = "PAUSED" if self.paused else "RUNNING"
        header = f"{status}   bodies={len(self.sim.bodies)}   speed={self.time_scale:g}x   zoom={self.zoom:.2f}x"
        self.screen.blit(self.font.render(header, True, TEXT), (16, 14))

        controls = [
            "Left click: add body   Right click: remove nearest   Middle-drag: pan",
            "Mouse wheel: zoom   Space: pause   +/-: time speed   T: trails   R: reset   Esc/Q: quit",
        ]
        for i, line in enumerate(controls):
            self.screen.blit(self.small_font.render(line, True, MUTED), (16, 42 + 22 * i))

        pygame.display.flip()

    def run(self) -> None:
        running = True
        while running:
            for event in pygame.event.get():
                running = self.handle_event(event)
                if not running:
                    break
            self.update()
            self.draw()
            self.clock.tick(60)

        pygame.quit()


def main() -> int:
    try:
        GravityApp().run()
        return 0
    except pygame.error as exc:
        print(f"Pygame could not start: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
