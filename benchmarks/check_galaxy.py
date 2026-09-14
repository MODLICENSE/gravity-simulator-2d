"""Seeded orbit-duration validation of the actual production physics engine.

Outputs JSON snapshots: energy, angular momentum, radial mass quantiles,
instantaneous positive-energy fraction, and mass outside twice the initial edge.
Positive individual energy in a time-dependent N-body field is a diagnostic,
not a proof of eventual escape. All stars have equal masses in the new preset.
"""
import argparse
import json
import math
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from galaxy import spiral_galaxy, BACKGROUND, SOFTENING, OUTER_RADIUS, circular_speed_squared
from gravity_sim import NBodySimulation


def diagnostics(sim):
    bs = sim.bodies
    radii = sorted(math.hypot(b.x,b.y) for b in bs)
    phi = [sim.background.potential(b.x,b.y,sim.G) if sim.background else 0 for b in bs]
    for i,b in enumerate(bs):
        for j in range(i+1,len(bs)):
            c=bs[j]
            inv = sim.G/math.sqrt((b.x-c.x)**2+(b.y-c.y)**2+sim.softening**2)
            phi[i] -= c.mass*inv
            phi[j] -= b.mass*inv
    positive = sum(b.mass for b,p in zip(bs,phi) if .5*(b.vx*b.vx+b.vy*b.vy)+p > 0)
    return {'energy':sim.total_energy(),
            'angular_momentum':sum(b.mass*(b.x*b.vy-b.y*b.vx) for b in bs),
            'r50':radii[len(radii)//2], 'r90':radii[int(.9*len(radii))],
            'positive_energy_mass_fraction':positive/sum(b.mass for b in bs),
            'outside_2R_mass_fraction':sum(b.mass for b in bs if math.hypot(b.x,b.y)>2*OUTER_RADIUS)/sum(b.mass for b in bs)}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--count',type=int,default=256)
    p.add_argument('--orbits',type=float,default=3)
    p.add_argument('--dt',type=float,default=1)
    p.add_argument('--solvers',nargs='+',default=['exact','barnes-hut','fmm'])
    p.add_argument('--seed',type=int,default=42)
    p.add_argument('--output',type=Path)
    args=p.parse_args()
    if args.dt<=0 or args.orbits<=0:
        p.error('dt and orbits must be positive')
    # Reference period at two exponential scale lengths, same for all solvers.
    period=math.tau*400/math.sqrt(circular_speed_squared(400))
    report={'count':args.count,'seed':args.seed,'dt':args.dt,'reference_period':period,'runs':{}}
    for solver in args.solvers:
        sim=NBodySimulation(spiral_galaxy(args.count,seed=args.seed),solver=solver,
                            softening=SOFTENING,background=BACKGROUND)
        history=[dict(time=0,**diagnostics(sim))]
        steps=math.ceil(args.orbits*period/args.dt)
        dt=args.orbits*period/steps
        for step in range(1,steps+1):
            sim.step(dt)
            if step%max(1,steps//6)==0 or step==steps:
                row=dict(time=step*dt,**diagnostics(sim));history.append(row)
                print(solver,args.count,round(row['time']/period,2),'orbits',
                      'dE',round((row['energy']-history[0]['energy'])/abs(history[0]['energy']),6),
                      'r50 ratio',round(row['r50']/history[0]['r50'],3),flush=True)
        report['runs'][solver]=history
    if args.output:
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(json.dumps(report,indent=2)+'\n')
    else:
        print(json.dumps(report,indent=2))


if __name__=='__main__':
    main()
