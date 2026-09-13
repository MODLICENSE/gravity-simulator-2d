from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Iterable


@dataclass
class Body:
    """A point-mass body for the 2D gravity simulation."""

    x: float
    y: float
    vx: float
    vy: float
    mass: float
    radius: float = 6.0
    color: tuple[int, int, int] = (240, 240, 240)
    name: str = "Body"


class NBodySimulation:
    """Small educational 2D Newtonian N-body simulator.

    Units are intentionally abstract. With G=1.0, positions, masses, velocities,
    and time steps can be chosen for visually convenient orbital motion.
    """

    def __init__(
        self,
        bodies: Iterable[Body] | None = None,
        *,
        gravitational_constant: float = 1.0,
        softening: float = 3.0,
    ) -> None:
        self.bodies = list(bodies or [])
        self.G = float(gravitational_constant)
        self.softening = float(softening)

    def accelerations(self) -> list[tuple[float, float]]:
        """Return acceleration on each body from every other body."""
        n = len(self.bodies)
        acc = [[0.0, 0.0] for _ in range(n)]
        eps2 = self.softening * self.softening

        # Pairwise update preserves Newton's third-law symmetry and reduces work.
        for i in range(n):
            a = self.bodies[i]
            for j in range(i + 1, n):
                b = self.bodies[j]
                dx = b.x - a.x
                dy = b.y - a.y
                r2 = dx * dx + dy * dy + eps2
                inv_r3 = 1.0 / (r2 * math.sqrt(r2))

                factor_i = self.G * b.mass * inv_r3
                factor_j = self.G * a.mass * inv_r3

                acc[i][0] += dx * factor_i
                acc[i][1] += dy * factor_i
                acc[j][0] -= dx * factor_j
                acc[j][1] -= dy * factor_j

        return [(ax, ay) for ax, ay in acc]

    def step(self, dt: float) -> None:
        """Advance one time step using velocity-Verlet integration.

        Velocity-Verlet is noticeably more stable for orbital systems than
        explicit Euler while remaining compact and easy to understand.
        """
        if not self.bodies:
            return

        a0 = self.accelerations()
        half_dt2 = 0.5 * dt * dt

        for body, (ax, ay) in zip(self.bodies, a0):
            body.x += body.vx * dt + ax * half_dt2
            body.y += body.vy * dt + ay * half_dt2

        a1 = self.accelerations()
        half_dt = 0.5 * dt

        for body, (ax0, ay0), (ax1, ay1) in zip(self.bodies, a0, a1):
            body.vx += (ax0 + ax1) * half_dt
            body.vy += (ay0 + ay1) * half_dt

    def total_momentum(self) -> tuple[float, float]:
        px = sum(body.mass * body.vx for body in self.bodies)
        py = sum(body.mass * body.vy for body in self.bodies)
        return px, py

    def total_energy(self) -> float:
        kinetic = sum(
            0.5 * body.mass * (body.vx * body.vx + body.vy * body.vy)
            for body in self.bodies
        )

        potential = 0.0
        eps2 = self.softening * self.softening
        for i, a in enumerate(self.bodies):
            for b in self.bodies[i + 1 :]:
                dx = b.x - a.x
                dy = b.y - a.y
                distance = math.sqrt(dx * dx + dy * dy + eps2)
                potential -= self.G * a.mass * b.mass / distance

        return kinetic + potential
