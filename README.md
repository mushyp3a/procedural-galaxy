# Procedural Galaxy

A galaxy generator with an interactive 3D viewer. It runs entirely in the browser, so no Python or server setup is needed.

The Generator is hosted here: https://mackenzietrafford.com/projects/galaxy/ but you can still run it locally as shown below.

The original Python and SQLite version lives on the `DEPRECATED-python-sqlite-version` branch. It may no longer work.

## Running It

The project is static files, so any simple server will do:

```
cd html
python -m http.server 8000
```

Then open http://localhost:8000.

## Files

```
html/
  index.html      The page and all the panels
  style.css       Styling, with the colours at the top
  generator.js    Generates the systems, stars, planets and moons
  viewer.js       Draws everything with three.js
  main.js         Config inputs and starting the generation
  viewer/
    three.min.js
    OrbitControls.js
```

The scripts load in this order in `index.html`, so `generator.js` must come before `viewer.js`.

## Viewer Features

- Every system is a point, coloured by metallicity (blue is low, orange is high).
- Click a system to fly in and see its stars, planets and moons on their orbits.
- Click a star, planet or moon to see its details.
- Search by system ID, or filter by metallicity, planet count and spectral type.
- `Esc` or the Back button returns to the galaxy view.
- `Space` centres the camera. Left-drag orbits, right-drag pans and the wheel zooms.
- The Generator Config in the search panel lets you change the seed, size, noise and orbit limits, then click Regenerate.
