import math
import unittest

from galaxy import (BACKGROUND, DISK_MASS, MAX_TIMESTEP, OUTER_RADIUS, SOFTENING,
                    circular_speed_squared, spiral_galaxy, surface_density, velocity_moments)
from gravity_sim import Body, NBodySimulation, PlummerBackground


class GalaxyTests(unittest.TestCase):
    def test_exponential_density_and_quiet_start(self):
        bs=spiral_galaxy(1200)
        self.assertEqual(bs,spiral_galaxy(1200))
        self.assertAlmostEqual(sum(b.mass for b in bs),DISK_MASS)
        for i in range(0,len(bs),2):
            self.assertEqual((bs[i].x,bs[i].y,bs[i].vx,bs[i].vy),
                             (-bs[i+1].x,-bs[i+1].y,-bs[i+1].vx,-bs[i+1].vy))
        norm=1-(1+OUTER_RADIUS/200)*math.exp(-OUTER_RADIUS/200)
        for r in (100,200,400,600):
            fraction=sum(math.hypot(b.x,b.y)<=r for b in bs)/len(bs)
            expected=(1-(1+r/200)*math.exp(-r/200))/norm
            self.assertLess(abs(fraction-expected),.005)
        self.assertAlmostEqual(sum(b.mass for b in spiral_galaxy(101)),DISK_MASS)

    def test_target_q_and_near_virial_balance(self):
        for r in range(20,800,20):
            mean,sr,sp,kappa=velocity_moments(r)
            self.assertGreaterEqual(sr*kappa/(3.36*surface_density(r)),1.6-1e-12)
            self.assertGreater(mean,0)
        sim=NBodySimulation(spiral_galaxy(400),background=BACKGROUND,softening=SOFTENING,solver='exact')
        a=sim.accelerations()
        twice_t=sum(b.mass*(b.vx*b.vx+b.vy*b.vy) for b in sim.bodies)
        w=sum(b.mass*(b.x*ax+b.y*ay) for b,(ax,ay) in zip(sim.bodies,a))
        self.assertLess(abs(twice_t/(-w)-1),.03)

    def test_background_force_is_negative_potential_gradient(self):
        x,y,h=123.,87.,1e-3
        ax,ay=BACKGROUND.acceleration(x,y)
        self.assertAlmostEqual(ax,-(BACKGROUND.potential(x+h,y)-BACKGROUND.potential(x-h,y))/(2*h),places=10)
        self.assertAlmostEqual(ay,-(BACKGROUND.potential(x,y+h)-BACKGROUND.potential(x,y-h))/(2*h),places=10)
        for solver in ('exact','barnes-hut','fmm'):
            s=NBodySimulation([Body(x,y,0,0,1)],solver=solver,background=BACKGROUND)
            self.assertEqual(s.accelerations(),[(ax,ay)])
            self.assertEqual(s.total_energy(),BACKGROUND.potential(x,y))

    def test_timestep_resolves_core_orbits(self):
        omega=math.sqrt(sum(m/a**3 for m,a in BACKGROUND.components))
        self.assertLess(MAX_TIMESTEP*omega,.1)
        radius=20
        ax,_=BACKGROUND.acceleration(radius,0)
        s=NBodySimulation([Body(radius,0,0,math.sqrt(-radius*ax),1)],background=BACKGROUND)
        e=s.total_energy()
        for _ in range(1000):
            s.step(MAX_TIMESTEP)
        self.assertLess(abs((s.total_energy()-e)/e),1e-5)


if __name__=='__main__':
    unittest.main()
