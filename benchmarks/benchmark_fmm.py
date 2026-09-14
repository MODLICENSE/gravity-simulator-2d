"""Reproducible force-only benchmark; run from the repository root."""
import argparse
import math
from pathlib import Path
import random
import statistics
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from gravity_sim import Body, NBodySimulation
from fmm import accelerations


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sizes', type=int, nargs='+', default=[200, 1000, 3000])
    parser.add_argument('--repeats', type=int, default=3)
    parser.add_argument('--theta', type=float, default=.5)
    args = parser.parse_args()
    if args.repeats < 1 or min(args.sizes) < 1:
        parser.error('sizes and repeats must be positive')
    print('N,solver,median_ms,relative_RMS_error,speedup_vs_exact')
    for n in args.sizes:
        rng = random.Random(42)
        bodies = [Body(rng.uniform(-100,100), rng.uniform(-100,100), 0, 0,
                       rng.uniform(.1,10)) for _ in range(n)]
        sim = NBodySimulation(bodies, softening=1)
        expected = None
        for solver in ('exact', 'barnes-hut', 'fmm'):
            sim.solver = solver
            sim.fmm_theta = args.theta
            times = []
            for _ in range(args.repeats):
                t = time.perf_counter()
                result = sim.accelerations()
                times.append(time.perf_counter()-t)
            elapsed = statistics.median(times)
            if expected is None:
                expected, exact_time = result, elapsed
            error = math.sqrt(sum((a-c)**2+(b-d)**2 for (a,b),(c,d) in zip(result,expected)) /
                              max(sum(a*a+b*b for a,b in expected), 1e-30))
            print(f'{n},{solver},{1000*elapsed:.3f},{error:.6g},{exact_time/elapsed:.2f}')
        stats = {}
        accelerations(bodies, softening=1, theta=args.theta, stats=stats)
        print(f'# N={n}: {stats}')


if __name__ == '__main__':
    main()
