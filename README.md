# Procedural Galaxy Generator

A procedural universe generator with an interactive 3D viewer. Two modes:

- **`universe.html`** — fully client-side, runs the entire generation pipeline in
  JavaScript. No Python or server required. All parameters are editable in the
  browser and the universe can be regenerated instantly.
- **Python pipeline** — generates into a SQLite database for offline analysis or
  to produce the legacy `explore.html`.

## Deploying to Hugo / GitHub Pages

Copy two things into your Hugo site's `static/` directory:

```
static/
  universe.html
  viewer/
    three.min.js
    OrbitControls.js
```

Then `universe.html` is available at `yoursite.com/universe.html`. No build step
needed — the page generates the universe in-browser on first load.

## Python pipeline (offline generation)

```bash
nix develop          # enter dev shell (numpy, noise, plotly)
python universe.py   # generate universe.db
python view.py       # write explore.html (legacy viewer, gitignored)
```

## Interactive viewer features

- **Universe view**: every system is a point in 3D space, coloured by metallicity,
  over a starfield. Drag to orbit, scroll to zoom, WASD to fly.
- **Click a system** (or use Search) to fly in. Stars are drawn with glow, planets
  on orbits with connecting edges.
- **Click a star or planet** to focus it and show its properties.
- **Search / Filter**: filter by metallicity range, planet count, spectral type.
  `Esc` / "Back" returns to the universe view.
- **Generator Config** (collapsible, in the Search panel): change any generation
  parameter — seed, universe size, noise scale, lattice resolution, element
  thresholds, star and orbit limits — then click **Regenerate**.

> Moons are schema-supported but not yet generated.
