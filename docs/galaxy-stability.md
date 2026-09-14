# Galaxy equilibrium, stability, and numerical validation

## What was wrong with the original preset?

The previous generator put most disk particles into four narrow arms, used a
5,200-mass softened point core, and assigned circular speeds from a different,
spherical enclosed-mass prescription. For seed 42 the actual disk+bulge particles
sum to 1,387.98 mass units, whereas the velocity prescription uses independent
2,100 and 650 mass scales. Even matching those totals would not make the
spherical formula correct for a flattened, non-axisymmetric disk. The circular
speed calculation also ignored the core's softening.

More seriously, the old app enlarged physics dt when increasing speed: at 4096x
and its eight-substep galaxy cap, dt was 23.04. The central softened dynamical
time sqrt(epsilon^3/Mcore) was only 0.155. Such large steps cannot resolve inner
orbits. A higher-quality force approximation cannot repair unresolved time
integration. The alternative UI from main used an even smaller two-substep cap
for FMM, making dt still larger.

## Theory used before evolving the replacement

Density alone does not specify equilibrium: the distribution of velocities must
also be consistent with the gravitational field. A stationary phase-space
distribution satisfies the collisionless Boltzmann equation; functions of
integrals of motion provide equilibrium constructions (Jeans theorem).
[Yurin & Springel (2014)](https://academic.oup.com/mnras/article/444/1/62/1014053)
explain why galaxy initial conditions require more than drawing plausible
positions and assigning ad hoc speeds; their GALIC method solves a substantially
more complete equilibrium problem than this educational preset.

For an axisymmetric field, circular motion requires

    vc²(R) = R dPhi/dR,
    Omega² = vc²/R²,
    kappa² = (1/R) d(vc²)/dR + 2 vc²/R².

An exponential surface density Sigma(R) proportional to exp(-R/Rd) requires
sampling radius with probability proportional to R exp(-R/Rd), because annular
area grows with radius. Disk gravity must be evaluated using disk geometry.
See [Bovy, disk potentials](https://galaxiesbook.org/chapters/II-01.-Gravitation-in-Galactic-Disks_3-Gravitational-potentials-from-disk-density-distributions.html).

Local stellar-disk stability is guided by

    Q = sigma_R kappa / (3.36 G Sigma) > 1.

A cold disk can clump under self-gravity; velocity dispersion and orbital
restoring forces oppose this. Q>1 addresses local axisymmetric disturbances,
not every bar, lopsided mode, or global instability. A halo can strengthen
orbital restoring forces. See [Bovy, disk stability](https://galaxiesbook.org/chapters/IV-04.-Internal-Evolution-in-Galaxies_1-The-%28in%29stability-of-disks.html).

A useful necessary bulk check is 2T + W approximately 0, with
W = sum m r dot a. This force virial includes the external field and softened
self-force. It must not be replaced blindly by the unsoftened isolated-system
potential energy. Virial balance alone does not prove equilibrium or stability.

Remaining bound and retaining the same arm geometry are different requirements.
Differential rotation shears material arms, and real spiral patterns can be
transient, self-excited, or driven. [Sellwood's discussion](https://ned.ipac.caltech.edu/level5/Sept13/Sellwood/Sellwood3.html)
explains why changes in the arms need not indicate a galaxy is disintegrating.
No force pins stars to the initial spirals in this implementation.

## Replacement model

- A 1,200-mass exponential stellar disk, Rd=200, truncated at R=850. Total disk
  mass stays fixed when particle count changes. The stars are equal-mass
  simulation particles, not literal individual-star masses.
- Two fixed Plummer components centered at the origin: bulge (M=1,800, a=65)
  and halo (M=18,000, a=450). Their potential is
  Phi=-G sum M/sqrt(R²+a²), and their force is included in every solver.
- The halo and bulge are smooth external fields, not live particles. They do not
  recoil or respond to the disk, and are not calibrated Milky Way parameters.
  Particle momentum alone need not be conserved in this external field. Stellar
  energy includes its potential, and the spherical background exerts no torque
  about its fixed center.
- Circular speeds use a numerical azimuthally averaged exponential-disk force
  calculation with the same Plummer softening (12) as the production solver,
  plus the exact background force. A cached radial table keeps startup quick.
- Radial dispersion targets Q=1.6 (with a small floor). Azimuthal dispersion uses
  the epicycle relation, and mean rotation uses an approximate radial Jeans
  correction. This is a near-circular initialization, not an exact positive
  distribution-function solution. The sharp outer truncation, finite-N noise,
  and spiral perturbations can still cause relaxation.
- Only 18% of the candidate disk stars above R=70 are drawn near spiral arms;
  the remainder fill the disk. The default four-arm perturbation uses a
  22-degree logarithmic pitch. Antipodal pairs and seed 42 give a reproducible
  quiet start. General odd arm counts are not guaranteed by this paired layout.

For the default 1,200-star realization, the initial force-virial ratio is 1.0079.
The Q target is a design heuristic based on an unsoftened thin-disk criterion;
softening, finite sampling and nonaxisymmetric structure change the actual
stability problem. None of these initial checks is a stability certificate.

## Speed is separate from timestep

`FixedStepClock` defaults to dt=0.5 for the galaxy and dt=0.045 for other presets.
Page Up/Page Down explicitly double/halve dt over a bounded 1/4x–16x range;
0 restores the preset default. Manual changes clear backlog and the speed
average. dt is constant between these user edits. COARSE marks multipliers
above 2x; this is an indicator, not a validated error bound.
The nominal 1x rate is 2.7 simulation units per real second, matching the old
.045-per-frame rate at 60 FPS. The speed multiplier changes the number of steps due, never dt; the separate
timestep controls make that accuracy tradeoff explicit.
A 12-ms physics work budget permits additional steps when CPU time is available.
A single force evaluation can itself exceed the budget; it cannot be interrupted.

If hardware cannot deliver the requested speed, excess whole-step backlog is
discarded and achieved/requested speed is displayed. This prevents an endless
catch-up queue and numerically destructive large timesteps. Pausing clears the
accumulator. The fixed dt values are preset choices, not guarantees for every
user-created massive body or unusually close encounter.

[`async/await`](https://docs.python.org/3/library/asyncio-dev.html) does not accelerate CPU calculations. Pure-Python threads are
limited by the [GIL in standard CPython](https://docs.python.org/3/library/threading.html). A worker process can decouple UI latency,
but needs snapshot transfer, edit synchronization, and Windows spawn handling.
Compiled/vectorized kernels can offer speedups; this change does not claim
parallel execution. The other chat's interpolation FMM is preserved independently
in `experimental/interpolation_fmm.py`, requiring NumPy. One 1,200-star force-only
comparison gave Cartesian 0.048 s / 0.739% error versus interpolation 0.539 s /
0.0346% error. These compare self-forces only, with different default accuracy
settings; they are not equal-accuracy or isolated benchmark timings.

## Measured evolution

The committed JSON files in `benchmarks/results/` were generated with the actual
production `NBodySimulation.step`, including both self-gravity and background.
The reference orbit is at R=400: period approximately 563 simulation time units.
All runs use seed 42. dt=1 tests are twice the production galaxy timestep.

| N | Solver | Reference orbits | dt | Final R50 change | Final R90 change | Maximum sampled relative energy drift |
|---:|---|---:|---:|---:|---:|---:|
| 1,200 | FMM | 2 | 1 | +0.49% | +1.62% | 0.00072% |
| 1,200 | Barnes-Hut | 2 | 1 | +1.28% | +0.76% | 0.0213% |
| 256 | Exact | 3 | 1 | +6.56% | +5.73% | 0.000232% |
| 256 | Barnes-Hut | 3 | 1 | +2.25% | +5.47% | 0.0563% |
| 256 | FMM | 3 | 1 | +0.08% | +1.34% | 0.00332% |
| 256 | FMM | 3 | 0.5 | -0.91% | +2.52% | 0.00331% |

Every run had zero positive-energy mass and zero mass beyond twice the initial
outer radius at the recorded snapshots. Individual positive energy in a changing
N-body field is only an escape diagnostic. R50/R90 are particle-number quantiles,
equivalent to mass quantiles for the new equal-mass disk. Energy drift is measured
against exact softened potential energy including the background, sampled roughly
every half/third orbit, not continuously.

The exact low-N run spreads more than the full preset: a reminder that finite-N
relaxation, initialization, and approximation all matter. The half-step run
supports the broad confinement result, but these data do not establish precise
trajectory convergence or infinite-time equilibrium. They test a few rotations
of one seed, not billions of years, every seed, or permanent spiral arms.

For the legacy preset, 15 FMM steps at the former dt=23.04 changed energy from
-31,149 to +2,063,691 and R90 from 724 to 7,950. A separate equal-duration
Barnes-Hut coarse/fine comparison is recorded in `legacy-timestep-comparison.json`: over t=46.08, dt=23.04 changed energy from -31,149 to +2,062,380, while dt=0.09996 ended at -31,139 with no positive-energy particles. This isolates timestep size while holding the initial state and force solver fixed.
The legacy generator can be recovered from main's pre-merge commit a051f13;
these legacy experiments are distinct from the new preset validation.

Reproduce the replacement tests from the repository root:

```powershell
py -m unittest discover -s tests -v
py benchmarks/check_galaxy.py --count 256 --orbits 3 --output benchmarks/results/galaxy-256.json
py benchmarks/check_galaxy.py --count 1200 --orbits 2 --solvers barnes-hut fmm --output benchmarks/results/galaxy-1200.json
py benchmarks/check_galaxy.py --count 256 --orbits 3 --dt .5 --solvers fmm --output benchmarks/results/galaxy-256-halfstep.json
```

Validation ran on Linux. Windows compatibility is covered by the configured CI
matrix but is not inferred from these Linux results.

## Appearance versus mass

`galaxy_render.py` draws the existing smooth bulge as a projected Plummer-like
light profile plus unresolved-star grain. This does not introduce additional
N-body particles or modify force parameters. Disk colors and visual radii were
changed to a violet/magenta/blue palette; all physical initial conditions are
bit-for-bit identical. The colors are stylized, not stellar temperature data.
The Milky Way has an elongated/barred central bulge, unlike this spherical
approximation ([ESA](https://www.esa.int/ESA_Multimedia/Images/2018/05/Anatomy_of_the_Milky_Way)).

## Manual larger-step checks

Full 1,200-star FMM preset, seed 42, two reference orbits:

| Requested dt | Relative to default | Final R50 change | Max sampled energy drift | Final positive-energy fraction |
|---:|---:|---:|---:|---:|
| 4 | 8x | 0.87% | 0.00161% | 0 |
| 8 | 16x | 1.62% | 0.00887% | 0 |

The diagnostic uses a slightly shortened constant dt to end at exactly two orbits.
Additional 256-star, three-orbit checks at dt=2,4,8 are also committed. These
support using larger steps for visual exploration of this preset; they do not
establish accuracy for every encounter, altered mass distribution, or long run.
A larger timestep advances more time per force evaluation, not faster force
evaluations. Start at dt=2 or 4 and compare with a default-step reset.
