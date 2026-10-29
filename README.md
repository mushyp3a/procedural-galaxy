![alt text](/images/galaxy.png?)

# Procedural Galaxy

An interactive 3D galaxy generator, generated entirely in the browser from a seed value. Generated using layers of 3D perlin noise representing gas density, metallicity and various element densities (Hydrogen, Oxygen, Carbon, Helium). The perlin maps are sampled in a grid, then the points are filtered by adjustable parameters (minimum density, hydrogen and helium thresholds), above which a system may be created.

Once the system regions have been identified the exact coordinates are randomly placed in the region of space represented by the sampled point. Metallicity then effects the distribution of types of planets and stars, the number of celestial bodies, and their radii.

Planet formation efficiency scales with metallicity, with the snow line determining whether bodies form as terrestrials, ice giants, or gas giants. Star masses are drawn from a realistic initial mass function, producing spectral types from M dwarfs to O giants. Moons are placed within each planet’s Hill sphere and outside its Roche limit. The remaining element densities are tracked per region and can be seen in the system explorer.

The Generator is hosted here: https://mackenzietrafford.com/procedural-galaxy/ but you can still run it locally as shown below.

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

## Images

![alt text](/images/galaxy.png?)

![Solar System](/images/solar-system.png?)

![Planets](/images/planets.png?)
