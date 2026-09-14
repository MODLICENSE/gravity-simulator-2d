"""Symmetric, order-3 Cartesian FMM for Plummer-softened planar gravity.

Original implementation following the cell-cell/local-expansion construction
in Dehnen (2014), https://arxiv.org/abs/1405.2255 (Appendix A.1).
The kernel is 1/sqrt(x*x+y*y+eps*eps), NOT the 2D logarithmic kernel.
"""
from __future__ import annotations

import math


class _Cell:
    __slots__ = ('x', 'y', 'mass', 'radius', 'qxx', 'qxy', 'qyy',
                 'indices', 'children', 'local')

    def __init__(self, bodies, indices, capacity, depth=0):
        self.indices = indices
        self.children = []
        self.local = [0.0] * 9  # acceleration, symmetric Jacobian, symmetric Hessian
        self.mass = sum(bodies[i].mass for i in indices)
        self.x = (sum(bodies[i].mass * bodies[i].x for i in indices) / self.mass
                  if self.mass else sum(bodies[i].x for i in indices) / len(indices))
        self.y = (sum(bodies[i].mass * bodies[i].y for i in indices) / self.mass
                  if self.mass else sum(bodies[i].y for i in indices) / len(indices))
        self.radius = max(math.hypot(bodies[i].x-self.x, bodies[i].y-self.y) for i in indices)
        self.qxx = self.qxy = self.qyy = 0.0
        if len(indices) > capacity and depth < 32 and self.radius > 1e-12:
            # Geometric midpoint avoids unbalanced splits around a massive star.
            mx = (min(bodies[i].x for i in indices) + max(bodies[i].x for i in indices)) / 2
            my = (min(bodies[i].y for i in indices) + max(bodies[i].y for i in indices)) / 2
            groups = [[], [], [], []]
            for i in indices:
                groups[(bodies[i].x >= mx) + 2*(bodies[i].y >= my)].append(i)
            self.children = [_Cell(bodies, g, capacity, depth+1) for g in groups if g]
            self.indices = []
            # M2M: translate central second moments up the tree.
            for c in self.children:
                dx, dy = c.x-self.x, c.y-self.y
                self.qxx += c.qxx + c.mass*dx*dx
                self.qxy += c.qxy + c.mass*dx*dy
                self.qyy += c.qyy + c.mass*dy*dy
        else:
            # P2M: monopole + central quadrupole; central dipole vanishes.
            for i in indices:
                b = bodies[i]
                dx, dy = b.x-self.x, b.y-self.y
                self.qxx += b.mass*dx*dx
                self.qxy += b.mass*dx*dy
                self.qyy += b.mass*dy*dy


def accelerations(bodies, gravitational_constant=1.0, softening=3.0,
                  theta=0.5, leaf_capacity=16, stats=None):
    """Return accelerations using mutual cell interactions and a downward pass.

    theta=0 disables approximation. 0 <= theta < 1 bounds the sum of cell
    radii / separation. Nonnegative finite masses and finite positions required.
    Zero-mass test particles are supported. Unsoftened coincident pairs raise
    ValueError (their physical acceleration is undefined).
    """
    if not math.isfinite(theta) or not 0 <= theta < 1:
        raise ValueError('FMM theta must satisfy 0 <= theta < 1')
    if not isinstance(leaf_capacity, int) or leaf_capacity < 1:
        raise ValueError('FMM leaf capacity must be a positive integer')
    if not math.isfinite(softening) or softening < 0:
        raise ValueError('FMM softening must be finite and nonnegative')
    if not math.isfinite(gravitational_constant):
        raise ValueError('Gravitational constant must be finite')
    for b in bodies:
        if b.mass < 0 or not all(map(math.isfinite, (b.x, b.y, b.mass))):
            raise ValueError('FMM requires finite positions and nonnegative finite masses')
    acc = [[0.0, 0.0] for _ in bodies]
    counts = {'cell_pairs': 0, 'direct_pairs': 0}
    eps2 = softening * softening
    if not bodies:
        if stats is not None:
            stats.update(counts)
        return []
    root = _Cell(bodies, list(range(len(bodies))), leaf_capacity)

    def direct(a, b, same):
        for k, i in enumerate(a.indices):
            bi = bodies[i]
            sources = b.indices[k+1:] if same else b.indices
            for j in sources:
                bj = bodies[j]
                dx, dy = bj.x-bi.x, bj.y-bi.y
                r2 = dx*dx + dy*dy + eps2
                if r2 == 0:
                    raise ValueError('Coincident bodies require positive softening')
                inv = 1 / (r2 * math.sqrt(r2))
                fx, fy = dx*inv, dy*inv
                acc[i][0] += bj.mass*fx
                acc[i][1] += bj.mass*fy
                acc[j][0] -= bi.mass*fx
                acc[j][1] -= bi.mass*fy
                counts['direct_pairs'] += 1

    def mutual(a, b, dx, dy, d2):
        # Derivatives of K(R) through degree 3, R = a.center - b.center.
        r2 = d2 + eps2
        inv3 = 1 / (r2 * math.sqrt(r2))
        inv5, inv7 = inv3/r2, inv3/(r2*r2)
        gx, gy = -dx*inv3, -dy*inv3
        xx, xy, yy = 3*dx*dx*inv5-inv3, 3*dx*dy*inv5, 3*dy*dy*inv5-inv3
        xxx = 9*dx*inv5 - 15*dx**3*inv7
        xxy = 3*dy*inv5 - 15*dx*dx*dy*inv7
        xyy = 3*dx*inv5 - 15*dx*dy*dy*inv7
        yyy = 9*dy*inv5 - 15*dy**3*inv7
        # M2L: constant includes source quadrupole. Linear/quadratic terms
        # use monopole to keep total potential expansion degree exactly 3.
        for target, source, sign in ((a, b, 1), (b, a, -1)):
            l, m = target.local, source.mass
            l[0] += sign*(m*gx + .5*(source.qxx*xxx + 2*source.qxy*xxy + source.qyy*xyy))
            l[1] += sign*(m*gy + .5*(source.qxx*xxy + 2*source.qxy*xyy + source.qyy*yyy))
            l[2] += m*xx
            l[3] += m*xy
            l[4] += m*yy
            l[5] += sign*m*xxx
            l[6] += sign*m*xxy
            l[7] += sign*m*xyy
            l[8] += sign*m*yyy
        counts['cell_pairs'] += 1

    def walk(a, b):
        if a is b:
            if not a.children:
                direct(a, a, True)
            else:
                for i, c in enumerate(a.children):
                    walk(c, c)
                    for d in a.children[i+1:]:
                        walk(c, d)
            return
        dx, dy = a.x-b.x, a.y-b.y
        d2 = dx*dx + dy*dy
        if theta > 0 and d2 > 0 and (a.radius+b.radius)**2 < theta*theta*d2:
            mutual(a, b, dx, dy, d2)
        elif not a.children and not b.children:
            direct(a, b, False)
        elif a.children and (not b.children or a.radius >= b.radius):
            for c in a.children:
                walk(c, b)
        else:
            for c in b.children:
                walk(a, c)

    def evaluate(l, dx, dy):
        return (l[0]+l[2]*dx+l[3]*dy+.5*l[5]*dx*dx+l[6]*dx*dy+.5*l[7]*dy*dy,
                l[1]+l[3]*dx+l[4]*dy+.5*l[6]*dx*dx+l[7]*dx*dy+.5*l[8]*dy*dy)

    def downward(cell):
        l = cell.local
        if cell.children:
            for c in cell.children:
                dx, dy = c.x-cell.x, c.y-cell.y
                ax, ay = evaluate(l, dx, dy)
                v = c.local
                v[0] += ax
                v[1] += ay
                v[2] += l[2]+l[5]*dx+l[6]*dy
                v[3] += l[3]+l[6]*dx+l[7]*dy
                v[4] += l[4]+l[7]*dx+l[8]*dy
                for k in range(5, 9):
                    v[k] += l[k]
                downward(c)
        else:
            for i in cell.indices:
                ax, ay = evaluate(l, bodies[i].x-cell.x, bodies[i].y-cell.y)
                acc[i][0] += ax
                acc[i][1] += ay

    walk(root, root)
    downward(root)
    if stats is not None:
        stats.update(counts)
    return [(gravitational_constant*x, gravitational_constant*y) for x, y in acc]
