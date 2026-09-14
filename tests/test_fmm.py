import math
import random
import unittest

from fmm import accelerations
from gravity_sim import Body, NBodySimulation


def sample(n=300, clustered=False):
    rng = random.Random(731)
    return [Body(rng.gauss((i % 3)*100 if clustered else 0, 10 if clustered else 80),
                 rng.gauss(0, 10 if clustered else 80), 0, 0, rng.uniform(.1, 10))
            for i in range(n)]


def relative_rms(actual, expected):
    return math.sqrt(sum((a-c)**2+(b-d)**2 for (a,b),(c,d) in zip(actual, expected)) /
                     max(sum(a*a+b*b for a,b in expected), 1e-30))


class FMMTests(unittest.TestCase):
    def test_small_and_empty_systems(self):
        self.assertEqual(accelerations([]), [])
        self.assertEqual(accelerations([Body(4, 8, 0, 0, 2)]), [(0, 0)])
        bodies = [Body(-1, 0, 0, 0, 2), Body(1, 0, 0, 0, 2)]
        self.assertEqual(accelerations(bodies, softening=0), [(0.5, 0), (-0.5, 0)])

    def test_accuracy_and_tighter_acceptance(self):
        for clustered in (False, True):
            for eps in (0, 1, 100):
                bodies = sample(clustered=clustered)
                exact = NBodySimulation(bodies, softening=eps)._accelerations_exact()
                stats = {}
                approx = accelerations(bodies, softening=eps, stats=stats)
                tight = accelerations(bodies, softening=eps, theta=.25)
                self.assertGreater(stats['cell_pairs'], 0)
                self.assertLess(relative_rms(approx, exact), .02)
                self.assertLess(relative_rms(tight, exact), relative_rms(approx, exact))

    def test_zero_theta_is_direct(self):
        bodies = sample(80)
        expected = NBodySimulation(bodies)._accelerations_exact()
        stats = {}
        actual = accelerations(bodies, theta=0, stats=stats)
        self.assertLess(relative_rms(actual, expected), 1e-14)
        self.assertEqual(stats['direct_pairs'], 80*79//2)
        self.assertEqual(stats['cell_pairs'], 0)

    def test_mutual_expansions_conserve_force(self):
        bodies = sample(clustered=True)
        bodies[0].mass = 0  # test particle
        bodies[1].mass = 10000  # dominant central mass
        stats = {}
        actual = accelerations(bodies, stats=stats)
        self.assertGreater(stats['cell_pairs'], 0)
        scale = sum(b.mass*math.hypot(*a) for b, a in zip(bodies, actual))
        for k in (0, 1):
            self.assertLess(abs(sum(b.mass*a[k] for b, a in zip(bodies, actual))), 1e-13*scale)

    def test_coincident_softened_bodies_and_massless_cloud(self):
        bodies = [Body(0, 0, 0, 0, 1) for _ in range(50)]
        self.assertEqual(accelerations(bodies), [(0, 0)]*50)
        with self.assertRaises(ValueError):
            accelerations(bodies, softening=0)
        bodies = sample(50)
        for b in bodies:
            b.mass = 0
        self.assertEqual(accelerations(bodies), [(0, 0)]*50)

    def test_translation_and_gravity_scaling(self):
        bodies = sample()
        actual = accelerations(bodies)
        for b in bodies:
            b.x += 1000
            b.y -= 2000
        shifted = accelerations(bodies, gravitational_constant=2)
        self.assertLess(relative_rms(shifted, [(2*x, 2*y) for x,y in actual]), 1e-12)

    def test_simulation_dispatch_and_integration(self):
        sim = NBodySimulation(sample(100), solver='fmm')
        self.assertEqual(sim.active_solver, 'fmm')
        self.assertEqual(sim.accelerations(), accelerations(sim.bodies))
        for _ in range(10):
            sim.step(.01)
        self.assertLess(math.hypot(*sim.total_momentum()), 1e-11)
        sim.solver = 'exact'
        self.assertEqual(sim.accelerations(), sim._accelerations_exact())
        sim.solver = 'barnes-hut'
        self.assertEqual(sim.accelerations(), sim._accelerations_barnes_hut())

    def test_invalid_parameters(self):
        for theta in (-1, 1, float('nan')):
            with self.assertRaises(ValueError):
                accelerations([], theta=theta)
        with self.assertRaises(ValueError):
            accelerations([], leaf_capacity=0)
        with self.assertRaises(ValueError):
            accelerations([Body(0, 0, 0, 0, -1)])
        with self.assertRaises(ValueError):
            NBodySimulation(solver='typo')


if __name__ == '__main__':
    unittest.main()
