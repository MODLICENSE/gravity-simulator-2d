from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Iterable

import numpy as np


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


class _QuadNode:
    """Internal node for the Barnes-Hut quadtree."""

    __slots__ = ("cx", "cy", "half", "depth", "mass", "com_x", "com_y", "indices", "children")
    LEAF_CAPACITY = 4
    MAX_DEPTH = 32

    def __init__(self, cx: float, cy: float, half: float, depth: int = 0) -> None:
        self.cx = cx
        self.cy = cy
        self.half = half
        self.depth = depth
        self.mass = 0.0
        self.com_x = 0.0
        self.com_y = 0.0
        self.indices: list[int] = []
        self.children: list[_QuadNode] | None = None

    def contains(self, x: float, y: float) -> bool:
        return self.cx - self.half <= x <= self.cx + self.half and self.cy - self.half <= y <= self.cy + self.half

    def _child_index(self, x: float, y: float) -> int:
        return (1 if x >= self.cx else 0) + (2 if y >= self.cy else 0)

    def _subdivide(self) -> None:
        q = self.half * 0.5
        self.children = [
            _QuadNode(self.cx - q, self.cy - q, q, self.depth + 1),
            _QuadNode(self.cx + q, self.cy - q, q, self.depth + 1),
            _QuadNode(self.cx - q, self.cy + q, q, self.depth + 1),
            _QuadNode(self.cx + q, self.cy + q, q, self.depth + 1),
        ]

    def insert(self, body_index: int, bodies: list[Body]) -> None:
        body = bodies[body_index]
        new_mass = self.mass + body.mass
        if new_mass != 0.0:
            self.com_x = (self.com_x * self.mass + body.x * body.mass) / new_mass
            self.com_y = (self.com_y * self.mass + body.y * body.mass) / new_mass
        self.mass = new_mass

        if self.children is None:
            if len(self.indices) < self.LEAF_CAPACITY or self.depth >= self.MAX_DEPTH:
                self.indices.append(body_index)
                return
            old = self.indices
            self.indices = []
            self._subdivide()
            assert self.children is not None
            for idx in old:
                b = bodies[idx]
                self.children[self._child_index(b.x, b.y)].insert(idx, bodies)

        assert self.children is not None
        self.children[self._child_index(body.x, body.y)].insert(body_index, bodies)


class NBodySimulation:
    """2D softened Newtonian gravity with Exact, Barnes-Hut and FMM solvers.

    ``solver_mode`` can be ``auto``, ``exact``, ``barnes-hut`` or ``fmm``.
    Auto uses exact gravity below ``barnes_hut_threshold`` and Barnes-Hut above it.

    The FMM path is a kernel-independent interpolation FMM on a uniform quadtree:
    particle-to-multipole (P2M), multipole-to-multipole (M2M), multipole-to-local
    (M2L), local-to-local (L2L), local evaluation, plus exact near-field P2P.
    It directly approximates the simulator's softened inverse-square force kernel.
    """

    VALID_SOLVERS = ("auto", "barnes-hut", "fmm", "exact")

    def __init__(
        self,
        bodies: Iterable[Body] | None = None,
        *,
        gravitational_constant: float = 1.0,
        softening: float = 3.0,
        barnes_hut_theta: float = 0.7,
        barnes_hut_threshold: int = 64,
        solver_mode: str = "auto",
        fmm_order: int = 4,
        fmm_leaf_capacity: int = 24,
        fmm_max_level: int = 8,
    ) -> None:
        self.bodies = list(bodies or [])
        self.G = float(gravitational_constant)
        self.softening = float(softening)
        self.barnes_hut_theta = float(barnes_hut_theta)
        self.barnes_hut_threshold = int(barnes_hut_threshold)
        self.solver_mode = solver_mode if solver_mode in self.VALID_SOLVERS else "auto"
        self.fmm_order = max(3, int(fmm_order))
        self.fmm_leaf_capacity = max(4, int(fmm_leaf_capacity))
        self.fmm_max_level = max(2, int(fmm_max_level))

    @property
    def active_solver(self) -> str:
        if self.solver_mode != "auto":
            return self.solver_mode
        return "exact" if len(self.bodies) < self.barnes_hut_threshold else "barnes-hut"

    def cycle_solver(self) -> str:
        order = ("auto", "fmm", "barnes-hut", "exact")
        self.solver_mode = order[(order.index(self.solver_mode) + 1) % len(order)]
        return self.solver_mode

    def accelerations(self) -> list[tuple[float, float]]:
        solver = self.active_solver
        if solver == "exact":
            return self._accelerations_exact()
        if solver == "fmm":
            return self._accelerations_fmm()
        return self._accelerations_barnes_hut()

    def _accelerations_exact(self) -> list[tuple[float, float]]:
        n = len(self.bodies)
        acc = [[0.0, 0.0] for _ in range(n)]
        eps2 = self.softening * self.softening
        for i in range(n):
            a = self.bodies[i]
            for j in range(i + 1, n):
                b = self.bodies[j]
                dx = b.x - a.x
                dy = b.y - a.y
                r2 = dx * dx + dy * dy + eps2
                inv_r3 = 1.0 / (r2 * math.sqrt(r2))
                fi = self.G * b.mass * inv_r3
                fj = self.G * a.mass * inv_r3
                acc[i][0] += dx * fi
                acc[i][1] += dy * fi
                acc[j][0] -= dx * fj
                acc[j][1] -= dy * fj
        return [(ax, ay) for ax, ay in acc]

    def _build_quadtree(self) -> _QuadNode | None:
        if not self.bodies:
            return None
        min_x = min(b.x for b in self.bodies)
        max_x = max(b.x for b in self.bodies)
        min_y = min(b.y for b in self.bodies)
        max_y = max(b.y for b in self.bodies)
        cx = 0.5 * (min_x + max_x)
        cy = 0.5 * (min_y + max_y)
        span = max(max_x - min_x, max_y - min_y)
        half = max(0.5 * span * 1.000001, 1e-9)
        root = _QuadNode(cx, cy, half)
        for i in range(len(self.bodies)):
            root.insert(i, self.bodies)
        return root

    def _accelerations_barnes_hut(self) -> list[tuple[float, float]]:
        root = self._build_quadtree()
        if root is None:
            return []
        eps2 = self.softening * self.softening
        theta = self.barnes_hut_theta
        result: list[tuple[float, float]] = []
        for target_index, target in enumerate(self.bodies):
            ax = ay = 0.0
            stack = [root]
            while stack:
                node = stack.pop()
                if node.mass == 0.0:
                    continue
                if node.children is None:
                    for source_index in node.indices:
                        if source_index == target_index:
                            continue
                        source = self.bodies[source_index]
                        dx = source.x - target.x
                        dy = source.y - target.y
                        r2 = dx * dx + dy * dy + eps2
                        inv_r3 = 1.0 / (r2 * math.sqrt(r2))
                        f = self.G * source.mass * inv_r3
                        ax += dx * f
                        ay += dy * f
                    continue
                dx = node.com_x - target.x
                dy = node.com_y - target.y
                d2 = dx * dx + dy * dy
                d = math.sqrt(d2) if d2 else 0.0
                can = not node.contains(target.x, target.y) and d > 0.0 and (2.0 * node.half) / d < theta
                if can:
                    r2 = d2 + eps2
                    inv_r3 = 1.0 / (r2 * math.sqrt(r2))
                    f = self.G * node.mass * inv_r3
                    ax += dx * f
                    ay += dy * f
                else:
                    stack.extend(node.children)
            result.append((ax, ay))
        return result

    @staticmethod
    def _cheb_nodes(order: int) -> np.ndarray:
        return np.cos(np.pi * np.arange(order) / (order - 1))[::-1]

    @staticmethod
    def _barycentric_weights(nodes: np.ndarray) -> np.ndarray:
        p = len(nodes)
        w = np.ones(p, dtype=float)
        for j in range(p):
            product = 1.0
            for k in range(p):
                if j != k:
                    product *= nodes[j] - nodes[k]
            w[j] = 1.0 / product
        return w

    @staticmethod
    def _lagrange_basis(x: float, nodes: np.ndarray, weights: np.ndarray) -> np.ndarray:
        diff = x - nodes
        hits = np.where(np.abs(diff) < 1e-13)[0]
        if hits.size:
            out = np.zeros(len(nodes), dtype=float)
            out[hits[0]] = 1.0
            return out
        values = weights / diff
        return values / values.sum()

    def _basis_2d(self, x: float, y: float, nodes: np.ndarray, weights: np.ndarray) -> np.ndarray:
        lx = self._lagrange_basis(x, nodes, weights)
        ly = self._lagrange_basis(y, nodes, weights)
        return np.outer(ly, lx).reshape(-1)

    def _fmm_transfer_matrices(self, nodes: np.ndarray, weights: np.ndarray) -> list[np.ndarray]:
        p = len(nodes)
        m = p * p
        matrices: list[np.ndarray] = []
        for qy in (0, 1):
            for qx in (0, 1):
                mat = np.zeros((m, m), dtype=float)
                for jy, ny in enumerate(nodes):
                    py = 0.5 * ny + (-0.5 if qy == 0 else 0.5)
                    ly = self._lagrange_basis(py, nodes, weights)
                    for jx, nx in enumerate(nodes):
                        px = 0.5 * nx + (-0.5 if qx == 0 else 0.5)
                        lx = self._lagrange_basis(px, nodes, weights)
                        mat[:, jy * p + jx] = np.outer(ly, lx).reshape(-1)
                matrices.append(mat)
        return matrices

    def _accelerations_fmm(self) -> list[tuple[float, float]]:
        """Kernel-independent interpolation FMM for the softened gravity force.

        A fixed-order Chebyshev representation is translated up/down a uniform
        quadtree. Well-separated same-level cells use M2L translations; touching
        leaf cells are evaluated directly. For fixed order/capacity this is near
        O(N) and, unlike the Barnes-Hut treecode, shares far-field work by cell.
        """
        n = len(self.bodies)
        if n == 0:
            return []
        if n <= self.fmm_leaf_capacity:
            return self._accelerations_exact()

        pos = np.array([(b.x, b.y) for b in self.bodies], dtype=float)
        masses = np.array([b.mass for b in self.bodies], dtype=float)
        p = self.fmm_order
        nodes = self._cheb_nodes(p)
        bary = self._barycentric_weights(nodes)
        transfers = self._fmm_transfer_matrices(nodes, bary)
        m = p * p

        min_x, min_y = pos.min(axis=0)
        max_x, max_y = pos.max(axis=0)
        cx = 0.5 * (min_x + max_x)
        cy = 0.5 * (min_y + max_y)
        span = max(max_x - min_x, max_y - min_y)
        half = max(0.5 * span * 1.000001, 1e-9)

        level = 0
        while level < self.fmm_max_level and n / (4**level) > self.fmm_leaf_capacity:
            level += 1
        leaf_level = level
        cells_per_axis = 2**leaf_level
        leaf_size = 2.0 * half / cells_per_axis
        ix = np.floor((pos[:, 0] - (cx - half)) / leaf_size).astype(int)
        iy = np.floor((pos[:, 1] - (cy - half)) / leaf_size).astype(int)
        ix = np.clip(ix, 0, cells_per_axis - 1)
        iy = np.clip(iy, 0, cells_per_axis - 1)

        leaf_particles: dict[tuple[int, int], list[int]] = {}
        for i, (xcell, ycell) in enumerate(zip(ix, iy)):
            leaf_particles.setdefault((int(xcell), int(ycell)), []).append(i)

        active: list[set[tuple[int, int]]] = [set() for _ in range(leaf_level + 1)]
        active[leaf_level] = set(leaf_particles)
        for lev in range(leaf_level - 1, -1, -1):
            active[lev] = {(x // 2, y // 2) for x, y in active[lev + 1]}

        def cell_geometry(lev: int, key: tuple[int, int]) -> tuple[float, float, float]:
            size = 2.0 * half / (2**lev)
            xcell, ycell = key
            return (
                cx - half + (xcell + 0.5) * size,
                cy - half + (ycell + 0.5) * size,
                0.5 * size,
            )

        multipoles: list[dict[tuple[int, int], np.ndarray]] = [dict() for _ in range(leaf_level + 1)]
        for key, indices in leaf_particles.items():
            ccx, ccy, cell_half = cell_geometry(leaf_level, key)
            coeff = np.zeros(m, dtype=float)
            for body_index in indices:
                u = (pos[body_index, 0] - ccx) / cell_half
                v = (pos[body_index, 1] - ccy) / cell_half
                coeff += masses[body_index] * self._basis_2d(u, v, nodes, bary)
            multipoles[leaf_level][key] = coeff

        for lev in range(leaf_level - 1, -1, -1):
            for parent in active[lev]:
                coeff = np.zeros(m, dtype=float)
                for qy in (0, 1):
                    for qx in (0, 1):
                        child = (2 * parent[0] + qx, 2 * parent[1] + qy)
                        child_coeff = multipoles[lev + 1].get(child)
                        if child_coeff is not None:
                            coeff += transfers[qy * 2 + qx] @ child_coeff
                multipoles[lev][parent] = coeff

        local: list[dict[tuple[int, int], np.ndarray]] = [dict() for _ in range(leaf_level + 1)]
        for lev in range(leaf_level + 1):
            for key in active[lev]:
                local[lev][key] = np.zeros((2, m), dtype=float)

        eps2 = self.softening * self.softening
        kernel_cache: dict[tuple[int, int, int], tuple[np.ndarray, np.ndarray]] = {}

        for lev in range(2, leaf_level + 1):
            size = 2.0 * half / (2**lev)
            cell_half = 0.5 * size
            grid_x, grid_y = np.meshgrid(nodes * cell_half, nodes * cell_half)
            node_x = grid_x.reshape(-1)
            node_y = grid_y.reshape(-1)
            bound = 2 ** (lev - 1)

            for target_key in active[lev]:
                target_parent = (target_key[0] // 2, target_key[1] // 2)
                target_local = local[lev][target_key]
                for dpy in (-1, 0, 1):
                    for dpx in (-1, 0, 1):
                        source_parent = (target_parent[0] + dpx, target_parent[1] + dpy)
                        if source_parent[0] < 0 or source_parent[1] < 0 or source_parent[0] >= bound or source_parent[1] >= bound:
                            continue
                        for qy in (0, 1):
                            for qx in (0, 1):
                                source_key = (2 * source_parent[0] + qx, 2 * source_parent[1] + qy)
                                source_coeff = multipoles[lev].get(source_key)
                                if source_coeff is None:
                                    continue
                                dx_cell = source_key[0] - target_key[0]
                                dy_cell = source_key[1] - target_key[1]
                                if abs(dx_cell) <= 1 and abs(dy_cell) <= 1:
                                    continue

                                cache_key = (lev, dx_cell, dy_cell)
                                matrices = kernel_cache.get(cache_key)
                                if matrices is None:
                                    source_x = node_x + dx_cell * size
                                    source_y = node_y + dy_cell * size
                                    dx = source_x[None, :] - node_x[:, None]
                                    dy = source_y[None, :] - node_y[:, None]
                                    r2 = dx * dx + dy * dy + eps2
                                    inv_r3 = 1.0 / (r2 * np.sqrt(r2))
                                    matrices = (self.G * dx * inv_r3, self.G * dy * inv_r3)
                                    kernel_cache[cache_key] = matrices
                                target_local[0] += matrices[0] @ source_coeff
                                target_local[1] += matrices[1] @ source_coeff

        for lev in range(leaf_level):
            for child in active[lev + 1]:
                parent = (child[0] // 2, child[1] // 2)
                parent_local = local[lev].get(parent)
                if parent_local is None:
                    continue
                qx, qy = child[0] & 1, child[1] & 1
                t = transfers[qy * 2 + qx].T
                local[lev + 1][child][0] += t @ parent_local[0]
                local[lev + 1][child][1] += t @ parent_local[1]

        acc = np.zeros((n, 2), dtype=float)
        for key, indices in leaf_particles.items():
            ccx, ccy, cell_half = cell_geometry(leaf_level, key)
            leaf_local = local[leaf_level][key]
            for i in indices:
                basis = self._basis_2d((pos[i, 0] - ccx) / cell_half, (pos[i, 1] - ccy) / cell_half, nodes, bary)
                acc[i, 0] += basis @ leaf_local[0]
                acc[i, 1] += basis @ leaf_local[1]

            for dx_cell in (-1, 0, 1):
                for dy_cell in (-1, 0, 1):
                    nearby = leaf_particles.get((key[0] + dx_cell, key[1] + dy_cell))
                    if nearby is None:
                        continue
                    for i in indices:
                        for j in nearby:
                            if i == j:
                                continue
                            dx = pos[j, 0] - pos[i, 0]
                            dy = pos[j, 1] - pos[i, 1]
                            r2 = dx * dx + dy * dy + eps2
                            inv_r3 = 1.0 / (r2 * math.sqrt(r2))
                            factor = self.G * masses[j] * inv_r3
                            acc[i, 0] += dx * factor
                            acc[i, 1] += dy * factor

        return [(float(ax), float(ay)) for ax, ay in acc]

    def step(self, dt: float) -> None:
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
        return (
            sum(body.mass * body.vx for body in self.bodies),
            sum(body.mass * body.vy for body in self.bodies),
        )

    def total_energy(self) -> float:
        kinetic = sum(0.5 * b.mass * (b.vx * b.vx + b.vy * b.vy) for b in self.bodies)
        potential = 0.0
        eps2 = self.softening * self.softening
        for i, a in enumerate(self.bodies):
            for b in self.bodies[i + 1 :]:
                dx = b.x - a.x
                dy = b.y - a.y
                potential -= self.G * a.mass * b.mass / math.sqrt(dx * dx + dy * dy + eps2)
        return kinetic + potential
