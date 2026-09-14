"""Near-circular exponential stellar disk in a smooth bulge + halo.

This is an approximate Jeans/epicycle initialization, not a solved equilibrium
DF or a model of permanent spiral arms. See docs/galaxy-stability.md.
"""
from __future__ import annotations

from bisect import bisect_right
from functools import lru_cache
import math
import random

from gravity_sim import Body, PlummerBackground

DISK_MASS = 1200.0
SCALE_LENGTH = 200.0
OUTER_RADIUS = 850.0
SOFTENING = 12.0
MAX_TIMESTEP = 1.0
BACKGROUND = PlummerBackground(((1800.0, 65.0), (18000.0, 450.0)))
COLORS = [(235, 240, 255), (190, 210, 255), (150, 180, 255),
          (255, 238, 200), (255, 210, 155)]
_CDF_MAX = 1 - (1 + OUTER_RADIUS/SCALE_LENGTH)*math.exp(-OUTER_RADIUS/SCALE_LENGTH)


def surface_density(r):
    return DISK_MASS * math.exp(-r/SCALE_LENGTH) / (math.tau*SCALE_LENGTH**2*_CDF_MAX)


@lru_cache(maxsize=1)
def _rotation_table():
    # Axisymmetric softened disk quadrature; uses the actual disk geometry,
    # not the spherical enclosed-mass approximation. G=1 in this preset.
    rings, angles, samples = 128, 96, 170
    dr = OUTER_RADIUS/rings
    sources = []
    weights = [(k+.5)*dr*math.exp(-(k+.5)*dr/SCALE_LENGTH) for k in range(rings)]
    for k, weight in enumerate(weights):
        radius = (k+.5)*dr
        mass = DISK_MASS*weight/(sum(weights)*angles)
        for j in range(angles):
            angle = math.tau*(j+.5)/angles
            sources.append((radius*math.cos(angle), radius*math.sin(angle), mass))
    radii, speed2 = [], []
    for k in range(samples+1):
        r = OUTER_RADIUS*k/samples
        ax, _ = BACKGROUND.acceleration(r, 0)
        for x, y, mass in sources:
            dx = x-r
            r2 = dx*dx+y*y+SOFTENING**2
            ax += mass*dx/(r2*math.sqrt(r2))
        radii.append(r)
        speed2.append(max(0.0, -r*ax))
    return radii, speed2


def circular_speed_squared(r):
    radii, values = _rotation_table()
    k = min(max(bisect_right(radii, r)-1, 0), len(radii)-2)
    fraction = min(max((r-radii[k])/(radii[k+1]-radii[k]), 0), 1)
    return values[k]*(1-fraction)+values[k+1]*fraction


def velocity_moments(r):
    """Return mean azimuthal speed, radial/azimuthal dispersions, kappa.

    Q=1.6 is a local, unsoftened thin-disk design target, not a global
    stability certificate. Epicycle and radial Jeans corrections are approximate.
    """
    def moments(radius):
        radius = max(radius, 2.5)
        vc2 = circular_speed_squared(radius)
        h = 2.0
        derivative = (circular_speed_squared(radius+h)-circular_speed_squared(max(.1,radius-h))) / (radius+h-max(.1,radius-h))
        omega2 = vc2/radius**2
        kappa2 = max(derivative/radius+2*omega2, 1e-10)
        sigma_r = max(1.6*3.36*surface_density(radius)/math.sqrt(kappa2), .025*math.sqrt(vc2))
        sigma_phi2 = sigma_r**2*kappa2/(4*omega2)
        return vc2, sigma_r, sigma_phi2, math.sqrt(kappa2)
    vc2, sr, sp2, kappa = moments(r)
    lo, hi = max(r-2, 2.5), max(r+2, 4.5)
    srlo, srhi = moments(lo)[1], moments(hi)[1]
    dlogsr2 = (math.log(srhi**2)-math.log(srlo**2))/(hi-lo)
    # Radial Jeans equation (zero cross term): <v_phi>² = vc² +
    # sigma_R²[1 + d ln(Sigma sigma_R²)/d ln R] - sigma_phi².
    mean2 = vc2+sr**2*(1-r/SCALE_LENGTH+r*dlogsr2)-sp2
    return math.sqrt(max(mean2, 0)), sr, math.sqrt(sp2), kappa


def spiral_galaxy(star_count=1200, arm_count=4, *, seed=42, arm_fraction=.18):
    """Fixed total disk mass, exponentially declining density, mild arms.

    Antipodal pairs provide a quiet start for even counts. Seeded generation
    makes resets and solver comparisons reproducible. Arms are perturbations
    free to shear, not forced paths. The background must be attached to the sim.
    """
    if star_count < 2 or arm_count < 1 or not 0 <= arm_fraction <= 1:
        raise ValueError('Need >=2 stars, >=1 arm, and arm_fraction in [0,1]')
    rng = random.Random(seed)
    bodies = []
    for i in range((star_count+1)//2):
        target = ((i+rng.random())/((star_count+1)//2))*_CDF_MAX
        lo, hi = 0.0, OUTER_RADIUS
        for _ in range(40):
            r = (lo+hi)/2
            if 1-(1+r/SCALE_LENGTH)*math.exp(-r/SCALE_LENGTH) < target:
                lo = r
            else:
                hi = r
        r = max((lo+hi)/2, 2.5)
        arm = r > 70 and rng.random() < arm_fraction
        angle = (rng.randrange(arm_count)*math.tau/arm_count +
                 math.log(r/100)/math.tan(math.radians(22)) + rng.gauss(0,.18)
                 if arm else rng.random()*math.tau)
        mean, sr, sp, _ = velocity_moments(r)
        vr, vt = rng.gauss(0,sr), mean+rng.gauss(0,sp)
        x, y = r*math.cos(angle), r*math.sin(angle)
        vx = vr*math.cos(angle)-vt*math.sin(angle)
        vy = vr*math.sin(angle)+vt*math.cos(angle)
        color = COLORS[rng.randrange(3)] if arm else COLORS[rng.randrange(len(COLORS))]
        radius = 1.7 if arm else (1.5 if r < 100 else 1.1)
        for sign in (1, -1):
            if len(bodies) < star_count:
                bodies.append(Body(sign*x,sign*y,sign*vx,sign*vy,DISK_MASS/star_count,
                                   radius,color,f'Disk {len(bodies)+1}'))
    return bodies
