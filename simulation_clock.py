"""Wall-clock pacing with fixed physics dt and a bounded per-frame CPU budget."""
from __future__ import annotations

import math
import time


class FixedStepClock:
    def __init__(self, timestep=.045, budget_seconds=.012, max_steps=2048):
        if not math.isfinite(timestep) or timestep <= 0 or budget_seconds <= 0 or max_steps < 1:
            raise ValueError('Positive timestep, budget and step limit required')
        self.base_timestep = timestep
        self.timestep = timestep
        self.timestep_level = 0
        self.budget_seconds = budget_seconds
        self.max_steps = max_steps
        self.pending = 0.0
        self.effective_speed = 0.0
        self._wall = self._advanced = 0.0

    def adjust_timestep(self, direction=0):
        """Explicit accuracy/speed tradeoff: 1/4x through 16x the preset dt.

        direction=0 restores default. Changing dt drops pending time so switching
        cannot create a catch-up burst; desired speed remains a separate input.
        """
        level = 0 if direction == 0 else max(-2, min(4, self.timestep_level + (1 if direction > 0 else -1)))
        if level != self.timestep_level:
            self.timestep_level = level
            self.timestep = self.base_timestep * 2**level
            self.pending = self._wall = self._advanced = 0.0
            self.effective_speed = 0.0
        return self.timestep

    def advance(self, step, elapsed, speed, *, paused=False, clock=time.perf_counter):
        if paused:
            self.pending = self._wall = self._advanced = 0.0
            self.effective_speed = 0.0
            return 0
        if elapsed < 0 or speed < 0 or not math.isfinite(elapsed+speed):
            raise ValueError('Finite nonnegative elapsed time and speed required')
        # Preserve the old nominal 1x rate: .045 simulation units * 60 Hz.
        self.pending += min(elapsed, .25)*2.7*speed
        start = clock()
        count = 0
        while self.pending+1e-12 >= self.timestep and count < self.max_steps:
            step(self.timestep)
            self.pending = max(0.0, self.pending-self.timestep)
            count += 1
            if clock()-start >= self.budget_seconds:
                break
        # Never accumulate a catch-up spiral. Under overload simulate less
        # time, retain only a fractional step, and report achieved speed.
        if self.pending >= self.timestep:
            self.pending %= self.timestep
        self._wall += elapsed
        self._advanced += count*self.timestep
        if self._wall >= .5:
            self.effective_speed = self._advanced/(2.7*self._wall)
            self._wall = self._advanced = 0.0
        return count
