# 2D Gravity Simulator

A cross-platform Newtonian **N-body gravity simulator** written in Python with a Pygame interface.

## Features

- Exact pairwise Newtonian gravity for small systems
- **Barnes-Hut** quadtree solver for larger systems
- **Fast Multipole Method (FMM)** solver using a kernel-independent interpolation quadtree
- Runtime solver switching with `B`
- Velocity-Verlet integration
- Softened gravity for close encounters
- Startup scenario picker
- Solar System, binary-star, randomized, and spiral-galaxy presets
- Custom body colors, sizes, and masses
- Selectable moving reference frames centered on any body
- Simulation speed from 1/16x up to 4096x
- Windows, macOS, and Linux support with Python 3.10+

## Windows quick start

```powershell
gh repo clone MODLICENSE/gravity-simulator-2d
cd gravity-simulator-2d
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app.py
```

You can also launch with:

```powershell
.\run_windows.bat
```

## Startup scenarios

1. **Solar System** — Sun plus all eight planets with realistic relative masses and orbital-distance ratios.
2. **Binary Star System** — two stars orbit a common barycenter with circumbinary planets.
3. **Randomized System** — a new rotating multi-body system every time.
4. **Spiral Galaxy** — roughly 1,200 stars in a dense bulge plus four spiral arms.

Press `M` while simulating to return to scenario selection.

## Solvers

Press **`B`** while the simulation is running to cycle:

```text
Auto -> FMM -> Barnes-Hut -> Exact -> Auto
```

The HUD displays both the selected mode and the solver currently being used.

### Auto

`Auto` uses exact gravity for fewer than 64 bodies and Barnes-Hut for larger systems.

### Exact

Every pair of bodies is evaluated directly. This is the reference implementation and is O(n^2).

### Barnes-Hut

Barnes-Hut builds a quadtree and approximates sufficiently distant cells by their total mass at their center of mass. It is usually around O(n log n) and has low overhead, making it a strong choice for medium-sized systems.

The main tuning parameter is `barnes_hut_theta` in `NBodySimulation`.

### FMM

The FMM implementation is a **kernel-independent interpolation Fast Multipole Method** for the same softened inverse-square gravity kernel used by the rest of the simulator.

It performs the standard FMM stages:

```text
P2M -> M2M -> M2L -> L2L -> L2P
                    + exact near-field P2P
```

A uniform quadtree is used. Source distributions in each cell are represented at Chebyshev interpolation nodes. Well-separated cell interactions are translated once at the cell level and reused for all particles in the target cell, instead of traversing distant cells separately for every particle as Barnes-Hut does.

The main FMM settings in `NBodySimulation` are:

- `fmm_order` — interpolation order; higher is more accurate but more expensive
- `fmm_leaf_capacity` — target average number of bodies per leaf
- `fmm_max_level` — maximum uniform quadtree depth

The default UI uses order 4 and a leaf capacity of 48.

The FMM implementation is written in Python/NumPy for portability. It is intended as a real algorithmic implementation and comparison point, not as a replacement for highly optimized compiled FMM libraries. Depending on body count and distribution, the current Barnes-Hut implementation may still be faster in wall-clock time despite FMM's better asymptotic structure.

## Controls

| Control | Action |
|---|---|
| `B` | Cycle Auto / FMM / Barnes-Hut / Exact |
| Left click | Add a body using the selected color / size / mass |
| Right click | Remove the nearest body |
| Middle mouse drag | Pan camera in the world frame |
| Mouse wheel | Zoom |
| Space | Pause / resume |
| `+` / `-` | Double / halve simulation speed |
| `C` | Cycle new-body color |
| `[` / `]` | Make newly created bodies smaller / larger |
| `F`, then click body | Use that body as the moving reference frame |
| `F` while locked | Return to world frame |
| `T` | Toggle trails |
| `R` | Reset current scenario |
| `M` | Scenario menu |
| `Esc` / `Q` | Quit |

## Moving reference frames

If body `r` is selected as the reference,

```text
x'_i = x_i - x_r
v'_i = v_i - v_r
```

The physical integration remains in the original inertial coordinates. Trails are transformed using the selected body's historical positions too.

## Run the tests

```bash
python -m unittest discover -s tests -v
```

The tests include direct checks of exact gravity, Barnes-Hut accuracy, FMM accuracy relative to the exact solver, solver switching, momentum conservation, and empty-system handling.

## Project layout

```text
.
├── app.py                    # Small launcher
├── gravity_app.py            # Pygame UI, scenarios and controls
├── gravity_sim.py            # Exact + Barnes-Hut + FMM physics engine
├── tests/
│   └── test_gravity_sim.py
├── requirements.txt
├── run_windows.bat
├── LICENSE
└── README.md
```

## Notes

This is an educational simulator rather than a high-precision astrophysics package. The Solar System is simplified to 2D circularized starting orbits, and the spiral galaxy is a visually and dynamically interesting initial condition rather than a calibrated Milky Way model.
