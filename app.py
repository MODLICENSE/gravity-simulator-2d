from __future__ import annotations

import math
import random
import sys
from collections import deque
from dataclasses import dataclass

import pygame

from gravity_sim import Body, NBodySimulation

WIDTH, HEIGHT = 1100, 720
BACKGROUND = (10, 13, 22)
GRID = (26, 31, 44)
TEXT = (225, 230, 240)
MUTED = (150, 160, 180)
ACCENT = (95, 180, 255)
PANEL = (19, 24, 36)
PANEL_HOVER = (31, 39, 56)

PALETTE = [
    (140, 220, 255),
    (255, 150, 120),
    (180, 255, 160),
    (225, 180, 255),
    (255, 220, 110),
    (245, 245, 245),
    (120, 150, 255),
    (255, 110, 180),
]


@dataclass(frozen=True)
class Scenario:
    key: str
    title: str
    description: str


SCENARIOS = [
    Scenario("solar", "Solar System", "Sun + 8 planets with realistic relative masses and orbital spacing."),
    Scenario("binary", "Binary Star System", "Two stars orbiting each other with circumbinary planets."),
    Scenario("random", "Randomized System", "A fresh random star cluster / planetary system every time."),
]


def solar_system() -> list[Body]:
    """Solar System using realistic relative masses and semi-major-axis ratios.

    The model is intentionally 2D and circularized for a clean educational
    starting state. Distances are proportional to AU, masses are relative to
    the Sun, and visual radii are enlarged so planets remain visible.
    """
    au = 18.0
    sun = Body(0, 0, 0, 0, mass=1.0, radius=14, color=(255, 210, 80), name="Sun")

    # name, AU, solar masses, visual radius, color
    data = [
        ("Mercury", 0.387, 1.66e-7, 3.0, (170, 165, 155)),
        ("Venus", 0.723, 2.45e-6, 4.5, (220, 185, 105)),
        ("Earth", 1.000, 3.00e-6, 4.8, (70, 145, 255)),
        ("Mars", 1.524, 3.23e-7, 4.0, (215, 95, 65)),
        ("Jupiter", 5.203, 9.54e-4, 8.8, (220, 175, 125)),
        ("Saturn", 9.537, 2.86e-4, 8.0, (225, 200, 135)),
        ("Uranus", 19.191, 4.37e-5, 6.7, (135, 220, 230)),
        ("Neptune", 30.069, 5.15e-5, 6.5, (75, 115, 245)),
    ]

    bodies = [sun]
    # Spread initial phases so the display is visually interesting.
    phases = [0.2, 1.1, 2.2, 3.1, 4.0, 5.0, 0.9, 2.7]
    for (name, semi_major_au, mass, radius, color), phase in zip(data, phases):
        r = semi_major_au * au
        speed = math.sqrt(sun.mass / r)
        x = math.cos(phase) * r
        y = math.sin(phase) * r
        vx = -math.sin(phase) * speed
        vy = math.cos(phase) * speed
        bodies.append(Body(x, y, vx, vy, mass, radius, color, name))
    return bodies


def binary_system() -> list[Body]:
    """A compact binary-star system with circumbinary planets."""
    m1, m2 = 700.0, 520.0
    separation = 95.0
    total = m1 + m2
    r1 = separation * m2 / total
    r2 = separation * m1 / total
    omega = math.sqrt(total / separation**3)

    star_a = Body(-r1, 0, 0, -omega * r1, m1, 12, (255, 215, 120), "Helios A")
    star_b = Body(r2, 0, 0, omega * r2, m2, 10, (255, 150, 110), "Helios B")
    bodies = [star_a, star_b]

    for idx, (r, mass, radius, color) in enumerate(
        [
            (190.0, 5.0, 5.0, (100, 175, 255)),
            (285.0, 9.0, 6.0, (180, 240, 155)),
            (405.0, 15.0, 7.0, (215, 155, 240)),
        ],
        start=1,
    ):
        phase = 0.8 + idx * 1.7
        speed = math.sqrt(total / r)
        bodies.append(
            Body(
                math.cos(phase) * r,
                math.sin(phase) * r,
                -math.sin(phase) * speed,
                math.cos(phase) * speed,
                mass,
                radius,
                color,
                f"Circumbinary {idx}",
            )
        )
    return bodies


def randomized_system(count: int = 120) -> list[Body]:
    """Generate a randomized rotating system large enough to exercise Barnes-Hut."""
    star_mass = random.uniform(900.0, 1800.0)
    bodies = [
        Body(0, 0, 0, 0, star_mass, 14, (255, 210, 95), "Primary")
    ]

    for i in range(count):
        r = random.uniform(55.0, 520.0)
        phase = random.random() * math.tau
        tangent = math.sqrt(star_mass / r) * random.uniform(0.78, 1.18)
        radial = random.uniform(-0.15, 0.15)
        mass = 10 ** random.uniform(-1.0, 1.2)
        color = random.choice(PALETTE)
        radius = max(2.5, min(8.5, 2.4 + math.sqrt(mass)))
        bodies.append(
            Body(
                math.cos(phase) * r,
                math.sin(phase) * r,
                -math.sin(phase) * tangent + math.cos(phase) * radial,
                math.cos(phase) * tangent + math.sin(phase) * radial,
                mass,
                radius,
                color,
                f"Random {i + 1}",
            )
        )
    return bodies


def scenario_bodies(key: str) -> tuple[list[Body], float, float]:
    """Return bodies, softening, and suggested starting zoom for a scenario."""
    if key == "solar":
        return solar_system(), 0.08, 0.58
    if key == "binary":
        return binary_system(), 2.5, 0.95
    return randomized_system(), 3.0, 0.92


class GravityApp:
    def __init__(self) -> None:
        pygame.init()
        pygame.display.set_caption("2D Gravity Simulator")
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.RESIZABLE)
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("consolas", 18)
        self.small_font = pygame.font.SysFont("consolas", 15)
        self.big_font = pygame.font.SysFont("consolas", 34, bold=True)
        self.title_font = pygame.font.SysFont("consolas", 23, bold=True)

        self.mode = "menu"
        self.current_scenario = "solar"
        self.sim = NBodySimulation([], softening=3.0)
        self.paused = False
        self.show_trails = True
        self.time_scale = 1.0
        self.zoom = 1.0
        self.camera_x = 0.0
        self.camera_y = 0.0
        self.trails: list[deque[tuple[float, float]]] = []
        self.drag_start: tuple[float, float] | None = None

        self.spawn_color_index = 0
        self.spawn_radius = 6.0
        self.spawn_mass = 8.0
        self.menu_rects: dict[str, pygame.Rect] = {}

    def ensure_trails(self) -> None:
        while len(self.trails) < len(self.sim.bodies):
            self.trails.append(deque(maxlen=600))
        if len(self.trails) > len(self.sim.bodies):
            self.trails = self.trails[: len(self.sim.bodies)]

    def load_scenario(self, key: str) -> None:
        bodies, softening, zoom = scenario_bodies(key)
        self.current_scenario = key
        self.sim = NBodySimulation(bodies, softening=softening)
        self.trails = []
        self.ensure_trails()
        self.time_scale = 1.0
        self.zoom = zoom
        self.camera_x = self.camera_y = 0.0
        self.paused = False
        self.mode = "simulation"

    def reset(self) -> None:
        self.load_scenario(self.current_scenario)

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

    @property
    def spawn_color(self) -> tuple[int, int, int]:
        return PALETTE[self.spawn_color_index]

    def add_body(self, pos: tuple[int, int]) -> None:
        x, y = self.screen_to_world(*pos)
        angle = random.random() * math.tau
        speed = random.uniform(0.15, 1.0)
        self.sim.bodies.append(
            Body(
                x,
                y,
                math.cos(angle) * speed,
                math.sin(angle) * speed,
                mass=self.spawn_mass,
                radius=self.spawn_radius,
                color=self.spawn_color,
                name=f"Custom {len(self.sim.bodies) + 1}",
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

    def handle_menu_event(self, event: pygame.event.Event) -> bool:
        if event.type == pygame.QUIT:
            return False
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_ESCAPE, pygame.K_q):
                return False
            if event.key == pygame.K_1:
                self.load_scenario("solar")
            elif event.key == pygame.K_2:
                self.load_scenario("binary")
            elif event.key == pygame.K_3:
                self.load_scenario("random")
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for key, rect in self.menu_rects.items():
                if rect.collidepoint(event.pos):
                    self.load_scenario(key)
                    break
        return True

    def handle_simulation_event(self, event: pygame.event.Event) -> bool:
        if event.type == pygame.QUIT:
            return False
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_ESCAPE, pygame.K_q):
                return False
            if event.key == pygame.K_SPACE:
                self.paused = not self.paused
            elif event.key == pygame.K_r:
                self.reset()
            elif event.key == pygame.K_m:
                self.mode = "menu"
            elif event.key == pygame.K_t:
                self.show_trails = not self.show_trails
            elif event.key == pygame.K_c:
                self.spawn_color_index = (self.spawn_color_index + 1) % len(PALETTE)
            elif event.key in (pygame.K_RIGHTBRACKET, pygame.K_PERIOD):
                self.spawn_radius = min(30.0, self.spawn_radius + 1.0)
                self.spawn_mass = min(200.0, self.spawn_mass * 1.35)
            elif event.key in (pygame.K_LEFTBRACKET, pygame.K_COMMA):
                self.spawn_radius = max(2.0, self.spawn_radius - 1.0)
                self.spawn_mass = max(0.1, self.spawn_mass / 1.35)
            elif event.key in (pygame.K_EQUALS, pygame.K_PLUS, pygame.K_KP_PLUS):
                self.time_scale = min(4096.0, self.time_scale * 2.0)
            elif event.key in (pygame.K_MINUS, pygame.K_KP_MINUS):
                self.time_scale = max(0.0625, self.time_scale / 2.0)
        elif event.type == pygame.MOUSEWHEEL:
            factor = 1.12 ** event.y
            self.zoom = max(0.03, min(12.0, self.zoom * factor))
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

    def handle_event(self, event: pygame.event.Event) -> bool:
        if self.mode == "menu":
            return self.handle_menu_event(event)
        return self.handle_simulation_event(event)

    def update(self) -> None:
        if self.mode != "simulation":
            return

        if not self.paused:
            # High time multipliers should not mean thousands of Python loops.
            # We increase integration granularity gently and cap the CPU cost.
            total_dt = 0.045 * self.time_scale
            substeps = max(1, min(48, int(math.ceil(math.sqrt(self.time_scale)))))
            sub_dt = total_dt / substeps
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
            spacing_world *= math.ceil(35 / max(spacing_px, 0.001))

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

    def draw_menu(self) -> None:
        self.screen.fill(BACKGROUND)
        w, h = self.screen.get_size()
        title = self.big_font.render("Choose a Starting System", True, TEXT)
        subtitle = self.font.render("Click a template or press 1 / 2 / 3", True, MUTED)
        self.screen.blit(title, (w // 2 - title.get_width() // 2, 72))
        self.screen.blit(subtitle, (w // 2 - subtitle.get_width() // 2, 120))

        mouse = pygame.mouse.get_pos()
        card_w = min(780, w - 80)
        card_h = 118
        gap = 18
        top = 180
        self.menu_rects = {}

        for i, scenario in enumerate(SCENARIOS):
            rect = pygame.Rect((w - card_w) // 2, top + i * (card_h + gap), card_w, card_h)
            self.menu_rects[scenario.key] = rect
            color = PANEL_HOVER if rect.collidepoint(mouse) else PANEL
            pygame.draw.rect(self.screen, color, rect, border_radius=12)
            pygame.draw.rect(self.screen, ACCENT, rect, 2, border_radius=12)

            number = self.title_font.render(str(i + 1), True, ACCENT)
            title = self.title_font.render(scenario.title, True, TEXT)
            desc = self.small_font.render(scenario.description, True, MUTED)
            self.screen.blit(number, (rect.x + 22, rect.y + 19))
            self.screen.blit(title, (rect.x + 62, rect.y + 18))
            self.screen.blit(desc, (rect.x + 62, rect.y + 58))

        note = self.small_font.render(
            "Random mode starts with 120 bodies so Barnes-Hut is active immediately.", True, MUTED
        )
        self.screen.blit(note, (w // 2 - note.get_width() // 2, top + 3 * (card_h + gap) + 8))
        pygame.display.flip()

    def draw_simulation(self) -> None:
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
        solver = "Barnes-Hut" if len(self.sim.bodies) >= self.sim.barnes_hut_threshold else "Exact"
        header = (
            f"{status}   bodies={len(self.sim.bodies)}   solver={solver}   "
            f"speed={self.time_scale:g}x   zoom={self.zoom:.2f}x"
        )
        self.screen.blit(self.font.render(header, True, TEXT), (16, 14))

        spawn_text = (
            f"New body: radius={self.spawn_radius:.0f}  mass={self.spawn_mass:.2f}  "
            "color="
        )
        spawn_surface = self.small_font.render(spawn_text, True, MUTED)
        self.screen.blit(spawn_surface, (16, 43))
        swatch_x = 16 + spawn_surface.get_width() + 8
        pygame.draw.circle(self.screen, self.spawn_color, (swatch_x + 8, 51), 7)

        controls = [
            "Left click: add custom body   Right click: remove nearest   Middle-drag: pan",
            "C: color   [ / ]: smaller/larger body   +/-: speed (up to 4096x)   T: trails",
            "Mouse wheel: zoom   Space: pause   R: reset   M: scenario menu   Esc/Q: quit",
        ]
        for i, line in enumerate(controls):
            self.screen.blit(self.small_font.render(line, True, MUTED), (16, 68 + 21 * i))

        pygame.display.flip()

    def draw(self) -> None:
        if self.mode == "menu":
            self.draw_menu()
        else:
            self.draw_simulation()

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
