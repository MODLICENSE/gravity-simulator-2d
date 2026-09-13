# 2D Gravity Simulator

A small cross-platform Newtonian **N-body gravity simulator** written in Python.
The graphical app uses Pygame, while the physics engine is kept in a separate,
testable module.

## Features

- Newtonian gravity in 2D
- **Automatic Barnes-Hut acceleration** for larger systems (typically O(n log n))
- Exact pairwise gravity for small systems (O(n^2))
- Velocity-Verlet integration for better orbital stability than explicit Euler
- Softened gravity to reduce singular behavior during close encounters
- Interactive add/remove bodies
- Pause, reset, zoom, pan, time-speed controls, and orbital trails
- Runs on Windows, macOS, and Linux with Python 3.10+
- Unit tests for the physics core

## Windows quick start

1. Install **Python 3.10 or newer** from https://www.python.org/downloads/
2. Clone this repository.
3. Double-click `run_windows.bat`.

The batch file installs Pygame and starts the simulator.

### Windows terminal alternative

```powershell
py -m pip install -r requirements.txt
py app.py
```

## macOS / Linux

```bash
python3 -m pip install -r requirements.txt
python3 app.py
```

## Controls

| Control | Action |
|---|---|
| Left click | Add a random moving body at the cursor |
| Right click | Remove the nearest body |
| Middle mouse drag | Pan camera |
| Mouse wheel | Zoom |
| Space | Pause/resume |
| `+` / `-` | Increase/decrease simulation speed |
| `T` | Toggle trails |
| `R` | Reset the demo system |
| `Esc` or `Q` | Quit |

## Run the tests

No graphics window is needed for the physics tests:

```bash
python -m unittest discover -s tests -v
```

## How the physics works

For small systems the simulator evaluates every body-body force exactly. For
larger systems (64+ bodies by default), it automatically switches to the
**Barnes-Hut algorithm**. Barnes-Hut groups sufficiently distant bodies into
quadtree cells and approximates each cell by its total mass at its center of
mass. This reduces the usual O(n^2) force calculation to roughly O(n log n).

The main accuracy/speed control is `barnes_hut_theta` in `NBodySimulation`:

- Smaller theta (for example `0.4`) = more accurate, slower
- Default `0.7` = faster, moderate approximation
- Larger theta = faster, less accurate

`barnes_hut_threshold` controls when the simulator switches from exact pairwise
gravity to Barnes-Hut; the default is 64 bodies.

A small softening term is added to the squared distance to avoid extremely
large forces when two point masses nearly overlap.

The simulator advances positions and velocities with **velocity-Verlet**
integration. It requires two acceleration evaluations per step, but behaves
much better for orbital motion than naive forward Euler integration.

## Project layout

```text
.
├── app.py                    # Pygame UI and input handling
├── gravity_sim.py            # Physics engine + Barnes-Hut quadtree
├── tests/
│   └── test_gravity_sim.py   # Unit tests
├── requirements.txt
├── run_windows.bat
├── LICENSE
└── README.md
```

## Notes

This is an educational simulator, not a high-precision astrophysics package.
The default scene uses normalized units chosen to produce visually interesting
orbits on screen.
