import unittest
from simulation_clock import FixedStepClock


class ClockTests(unittest.TestCase):
    def test_speed_changes_step_count_not_dt(self):
        for speed in (1,16,4096):
            c=FixedStepClock()
            steps=[]
            c.advance(steps.append,1/60,speed,clock=lambda:0)
            self.assertEqual(len(steps),min(speed,c.max_steps))
            self.assertTrue(all(dt==.045 for dt in steps))

    def test_budget_and_no_catchup_after_slowdown(self):
        c=FixedStepClock(timestep=.5,budget_seconds=.01)
        ticks=iter((0,.02))
        steps=[]
        c.advance(steps.append,.1,4096,clock=lambda:next(ticks))
        self.assertEqual(steps,[.5])
        self.assertLess(c.pending,.5)
        c.advance(steps.append,0,1,clock=lambda:0)
        self.assertEqual(steps,[.5])

    def test_manual_dt_changes_throughput_and_clears_backlog(self):
        c=FixedStepClock(timestep=.5)
        c.pending=10
        self.assertEqual(c.adjust_timestep(1),1)
        self.assertEqual(c.pending,0)
        for _ in range(10):
            c.adjust_timestep(1)
        self.assertEqual(c.timestep,8)
        ticks=iter((0,.02))
        calls=[]
        c.advance(calls.append,.1,4096,clock=lambda:next(ticks))
        self.assertEqual(calls,[8])
        c.adjust_timestep()
        self.assertEqual(c.timestep,.5)
        self.assertEqual(c.pending,0)
        for _ in range(10):
            c.adjust_timestep(-1)
        self.assertEqual(c.timestep,.125)

    def test_pause_resets_accumulator(self):
        c=FixedStepClock(timestep=.5)
        c.advance(lambda dt:None,.1,1)
        self.assertGreater(c.pending,0)
        c.advance(lambda dt:self.fail(),10,1,paused=True)
        self.assertEqual(c.pending,0)
        self.assertEqual(c.effective_speed,0)

    def test_wallclock_accumulation_and_achieved_speed(self):
        c=FixedStepClock(timestep=.5)
        steps=[]
        for _ in range(60):
            c.advance(steps.append,1/60,2,clock=lambda:0)
        self.assertEqual(len(steps),10)
        self.assertAlmostEqual(c.pending,.4)
        self.assertGreater(c.effective_speed,1)
        self.assertLess(c.effective_speed,2.1)
