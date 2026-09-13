import math
import unittest

from gravity_sim import Body, NBodySimulation


class GravitySimulationTests(unittest.TestCase):
    def test_two_body_acceleration_is_symmetric(self):
        sim = NBodySimulation(
            [Body(-1, 0, 0, 0, 2), Body(1, 0, 0, 0, 2)],
            gravitational_constant=1.0,
            softening=0.0,
        )
        (a1x, a1y), (a2x, a2y) = sim.accelerations()
        self.assertAlmostEqual(a1x, 0.5)
        self.assertAlmostEqual(a2x, -0.5)
        self.assertAlmostEqual(a1y, 0.0)
        self.assertAlmostEqual(a2y, 0.0)

    def test_momentum_is_nearly_conserved(self):
        bodies = [
            Body(-20, 0, 0, -1, 10),
            Body(20, 0, 0, 1, 10),
        ]
        sim = NBodySimulation(bodies, softening=0.5)
        initial = sim.total_momentum()
        for _ in range(1000):
            sim.step(0.01)
        final = sim.total_momentum()
        self.assertTrue(math.isclose(initial[0], final[0], abs_tol=1e-9))
        self.assertTrue(math.isclose(initial[1], final[1], abs_tol=1e-9))

    def test_barnes_hut_matches_exact_reasonably_well(self):
        bodies = [
            Body(float(i % 10), float(i // 10), 0, 0, 1 + (i % 3))
            for i in range(100)
        ]
        exact_sim = NBodySimulation(
            bodies, softening=0.5, barnes_hut_threshold=10_000
        )
        fast_sim = NBodySimulation(
            bodies,
            softening=0.5,
            barnes_hut_threshold=0,
            barnes_hut_theta=0.5,
        )

        exact = exact_sim._accelerations_exact()
        approx = fast_sim.accelerations()

        mean_relative_error = 0.0
        for (ex, ey), (ax, ay) in zip(exact, approx):
            denom = max(math.hypot(ex, ey), 1e-12)
            mean_relative_error += math.hypot(ex - ax, ey - ay) / denom
        mean_relative_error /= len(bodies)

        self.assertLess(mean_relative_error, 0.05)

    def test_empty_simulation_can_step(self):
        sim = NBodySimulation()
        sim.step(0.1)
        self.assertEqual(sim.bodies, [])


if __name__ == "__main__":
    unittest.main()
