# 2D Gravity Simulator

A cross-platform Newtonian **N-body gravity simulator** written in Python with a Pygame interface.

## Features

- Newtonian gravity in 2D
- **Automatic Barnes-Hut acceleration** for larger systems (typically O(n log n))
- Exact pairwise gravity for small systems (O(n^2))
- Velocity-Verlet integration
- Startup scenario picker
- Solar System preset with realistic relative planetary masses and orbital-distance ratios
- Binary-star circumbinary preset
- Randomized 120-body system that immediately exercises Barnes-Hut
- Spiral galaxy preset with a dense bulge, four spiral arms, and about 1,200 stars
- Custom body colors, sizes, and masses
- Selectable moving reference frames centered on any body
- Simulation speed from 1/16x up to **4096x**
- Pause, reset, zoom, pan, and orbital trails
- Windows, macOS, and Linux support with Python 3.10+

## Windows quick start

Clone the repository, then enter it:

```powershell
gh repo clone MODLICENSE/gravity-simulator-2d
cd gravity-simulator-2d
```

Create and activate a virtual environment:

```powershell
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

When the program starts, choose one of four systems:

1. **Solar System** — Sun plus all eight planets. Relative masses and semi-major-axis ratios are based on the real Solar System, while visual radii are enlarged so the planets remain visible. Orbits are circularized and the model is 2D.
2. **Binary Star System** — two stars orbit a common barycenter with three circumbinary planets.
3. **Randomized System** — a new 120-body rotating system every time. This exceeds the Barnes-Hut threshold, so the fast solver is active immediately.
4. **Spiral Galaxy** — a Milky-Way-inspired initial condition with a dense central bulge, a massive core, four spiral arms, and roughly 1,200 stars. Barnes-Hut is active automatically.

Press `M` while simulating to return to the scenario menu.

### Spiral galaxy notes

The galaxy preset is intended as a visually interesting N-body system rather than a calibrated model of the real Milky Way. Its spiral structure is imposed in the initial state; after startup, every star evolves only under the normal gravity solver.

To keep the large system usable:

- Barnes-Hut is active automatically.
- Trails start **off** in the galaxy preset; press `T` if you want them.
- Galaxy trails use a shorter history buffer.
- Integration substeps are capped more aggressively once the simulation contains 500+ bodies.

## Controls

| Control | Action |
|---|---|
| Left click | Add a body using the currently selected color / size / mass |
| Right click | Remove the nearest body |
| Middle mouse drag | Pan camera while in the world frame |
| Mouse wheel | Zoom |
| Space | Pause / resume |
| `+` / `-` | Double / halve simulation speed (1/16x to 4096x) |
| `C` | Cycle the color of newly created bodies |
| `[` / `]` | Make newly created bodies smaller / larger |
| `F`, then left click a body | Lock the moving reference frame to that body |
| `F` while locked | Return to the normal world frame |
| `T` | Toggle trails |
| `R` | Reset the current scenario |
| `M` | Return to scenario selection |
| `Esc` or `Q` | Quit |

The HUD displays the current new-body radius, mass, color, and active reference frame.

## Moving reference frames

Press `F` and then click a body. The selected body becomes the stationary center of the display.

This is implemented as a coordinate transformation rather than by changing the physical state of the simulation. If body `r` is selected as the reference,

```text
x'_i = x_i - x_r
v'_i = v_i - v_r
```

so the selected body has zero displayed position and velocity while every other body's relative velocity is preserved. The underlying Newtonian integration continues in the original coordinates.

Trails are transformed using the reference body's historical positions as well, so they show motion in the selected moving frame rather than simply following the camera.

Press `F` again to release the reference frame.

## High-speed simulation

The time multiplier can be increased to **4096x**.

The integrator uses an adaptive/capped number of substeps instead of performing one extra Python loop for every unit of speed. That lets very large time multipliers remain usable without turning 1024x into literally 1024 full physics iterations every frame.

Very high multipliers necessarily trade numerical accuracy for elapsed simulated time. For close encounters or precise orbit inspection, reduce the speed.

## Barnes-Hut gravity

For small systems the simulator evaluates every body-body force exactly. For systems with 64 or more bodies by default, it automatically switches to the **Barnes-Hut algorithm**.

Barnes-Hut builds a quadtree and approximates sufficiently distant collections of bodies by their combined mass at their center of mass. This reduces the usual O(n^2) force calculation toward roughly O(n log n).

The main accuracy/speed control is `barnes_hut_theta` in `NBodySimulation`:

- Smaller theta such as `0.4` = more accurate, slower
- Default `0.7` = balanced
- Larger theta = faster, less accurate

`barnes_hut_threshold` controls when the simulator switches from exact gravity to Barnes-Hut; the default is 64 bodies.

## Run the tests

```bash
python -m unittest discover -s tests -v
```

## Project layout

```text
.
├── app.py                    # UI, scenario presets, controls
├── gravity_sim.py            # Physics engine + Barnes-Hut quadtree
├── tests/
│   └── test_gravity_sim.py   # Physics tests
├── requirements.txt
├── run_windows.bat
├── LICENSE
└── README.md
```

## Notes

This is an educational simulator rather than a high-precision astrophysics package. The Solar System preset uses realistic relative masses and orbital-distance ratios, but it is intentionally simplified to 2D circular orbits and uses enlarged display radii.