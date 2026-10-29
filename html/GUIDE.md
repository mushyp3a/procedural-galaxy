# index.html — code guide

Everything runs in a single HTML file. Open it in a browser and you get a
self-contained procedural universe: no server, no build step, no dependencies
beyond the two three.js files in `viewer/`.

The file has three distinct layers:

1. **Generation** — the same logic as the Python pipeline, re-implemented in JS
2. **Viewer** — a three.js 3-D scene that displays the generated data
3. **UI** — panels, filters, and the config form wired to the regeneration button

---

## How to run it

```
open html/index.html        # macOS
xdg-open html/index.html   # Linux
```

Or just drag the file into a browser. The `viewer/` folder must be next to the
file because the page loads three.js from `./viewer/three.min.js`.

---

## Layer 1 — Generation

### Randomness (`makePRNG`, lines 126–152)

The Python side uses `numpy.random.default_rng(seed)`. JavaScript doesn't have
an equivalent, so instead there's a seeded xorshift32 generator:

```js
function makePRNG(seed) {
  let s = ((seed | 0) >>> 0) || 1;
  function next() {
    s ^= s << 13; s ^= s >>> 17; s ^= s << 5;
    return (s >>> 0) / 4294967296;
  }
  return {
    next,
    uniform(a, b) { return a + next() * (b - a); },
    int(lo, hi)   { return lo + ((next() * (hi - lo)) | 0); },
    poisson(lam)  { /* Knuth algorithm */ },
    shuffle(arr)  { /* Fisher-Yates */ }
  };
}
```

It's not the same algorithm as NumPy's PCG64, so the same seed produces a
different universe. The API is identical to how the Python code calls the RNG:
`uniform(a, b)`, `int(lo, hi)` (exclusive upper bound, matching
`rng.integers`), `poisson(lam)`, and `shuffle`.

**To change the default seed:** edit the input in the HTML form:
```html
<input id="cfg-seed" type="number" value="125" class="wide"/>
```

You can also change it live in the browser via the ⚙ Generator Config panel.

---

### Noise field (`generateLattice`, lines 209–232)

This is the equivalent of `lattice.py`. The universe volume is divided into a
50×50×50 grid. Each cell gets six Perlin noise values: density, C, O, He, H,
and metallicity.

```js
function generateLattice(cfg) {
  const {seed, universeSize, elementNoiseScale, elementOctaves, latticeResolution: N} = cfg;

  // linspace(0, universeSize*noiseScale, N) rounded to 2 dp — matches Python
  const steps = new Float64Array(N);
  for (let i = 0; i < N; i++)
    steps[i] = Math.round(i / (N-1) * universeSize * elementNoiseScale * 100) / 100;

  // ...

  for (let zi=0; zi<N; zi++) for (let yi=0; yi<N; yi++) for (let xi=0; xi<N; xi++) {
    const idx = zi*N*N + yi*N + xi;
    const sx=steps[xi], sy=steps[yi], sz=steps[zi];
    const d = perlin01(sx, sy, sz, seed+6, elementOctaves);
    density[idx] = d;
    C[idx]   = perlin01(sx, sy, sz, seed+1, elementOctaves) * d;
    O[idx]   = perlin01(sx, sy, sz, seed+2, elementOctaves) * d;
    He[idx]  = perlin01(sx, sy, sz, seed+3, elementOctaves) * d;
    H[idx]   = perlin01(sx, sy, sz, seed+4, elementOctaves) * d;
    met[idx] = perlin01(sx, sy, sz, seed+5, elementOctaves);
  }
  return {density, H, He, C, O, met, N, steps};
}
```

The seed offsets (`seed+1` through `seed+6`) match `config.py` exactly:
`carbon_seed = seed+1`, `oxygen_seed = seed+2`, etc.

Element abundances (C, O, He, H) are multiplied by density — the same
reasoning as the Python: denser regions have more material. Metallicity is not,
because it's a composition ratio, not an amount.

The Perlin implementation (`perlin01`, lines 198–205) uses Ken Perlin's
reference permutation table. It returns values in [0, 1] by doing
`(raw + 1) * 0.5`.

**To make the universe sparser or denser:** change `Density thresh` in the
config panel, or change the default in the HTML:
```html
<input id="cfg-densityThresh" type="number" step="0.05" min="0" max="1" value="0.5" class="wide"/>
```

---

### System placement (`generateSystems`, lines 236–265)

Equivalent to `systems.py`. Scans every lattice cell, keeps the ones above the
density, H, and He thresholds as candidates, shuffles them, then accepts each
with probability `density × H × He`.

```js
function generateSystems(lattice, rng, cfg) {
  const candidates = [];
  for (let idx = 0; idx < N*N*N; idx++) {
    if (density[idx] <= densityThreshold) continue;
    if (H[idx] <= HThreshold) continue;
    if (He[idx] <= HeThreshold) continue;
    candidates.push(idx);
  }
  rng.shuffle(candidates);

  for (const idx of candidates) {
    if (rng.next() > density[idx] * H[idx] * He[idx]) continue;

    // decode 3D position from flat index
    const zi=(idx/(N*N))|0, rem=idx%(N*N), yi=(rem/N)|0, xi=rem%N;
    const maxOff = cellSize * 0.4;
    systems.push({
      id: systems.length+1,
      x: xi*cellSize + rng.uniform(-maxOff, maxOff),
      y: yi*cellSize + rng.uniform(-maxOff, maxOff),
      z: zi*cellSize + rng.uniform(-maxOff, maxOff),
      density: density[idx], H: H[idx], He: He[idx],
      C: C[idx], O: O[idx], metallicity: met[idx]
    });
  }
  return systems;
}
```

The `maxOff = cellSize * 0.4` jitter stops systems from sitting on a grid. The
0.4 factor means a system can move at most 40% of a cell width in any
direction, so cells can't swap neighbours.

---

### Stars (`_starMass`, `_starLuminosity`, `_starRadius`, `_starTemperature`, lines 270–358)

Direct port of `stars.py`. The Kroupa IMF, mass-luminosity relation, and
Stefan-Boltzmann chain all use the same numbers.

```js
// Kroupa IMF — two-part power law
function _starMass(rng) {
  const lW = _powerLawIntegral(0.179, 0.50, 1.3);
  const hW = Math.pow(0.5, 2.3-1.3) * _powerLawIntegral(0.50, 31.0, 2.3);
  return rng.next() < lW/(lW+hW)
    ? _samplePL(rng, 0.179, 0.50, 1.3)
    : _samplePL(rng, 0.50, 31.0, 2.3);
}

// piecewise log-linear mass → luminosity
function _starLuminosity(m) {
  const lm = Math.log10(m);
  if (m <= 0.45) return Math.pow(10, 2.028*lm - 0.976);
  if (m <= 0.72) return Math.pow(10, 4.572*lm - 0.102);
  if (m <= 1.05) return Math.pow(10, 5.743*lm - 0.007);
  if (m <= 2.40) return Math.pow(10, 4.329*lm + 0.010);
  if (m <= 7.0)  return Math.pow(10, 3.967*lm + 0.093);
  return Math.pow(10, 2.865*lm + 1.105);
}
```

For mass ≤ 1.5 M☉: radius is computed from the polynomial first, then
temperature from Stefan-Boltzmann. For heavier stars it goes the other way
around because the polynomial isn't reliable — temperature comes from the
mass-temperature fit, then radius falls out of Stefan-Boltzmann.

```js
function _generateStar(rng, system) {
  const mass = _starMass(rng);
  const luminosity = _starLuminosity(mass);
  let radius, temperature;
  if (mass <= 1.5) {
    radius      = _starRadius(mass, luminosity);
    temperature = _starTemperature(mass, luminosity, radius);
  } else {
    temperature = _starTemperature(mass);
    radius      = _starRadius(mass, luminosity);
  }
  return {mass, luminosity, radius, temperature,
    spectral_type: _starSpectralType(temperature),
    metallicity: system.metallicity};
}
```

**To change the maximum stars per system:** edit `Max stars/sys` in the config
panel, or change the default:
```html
<input id="cfg-maxStars" type="number" min="1" max="5" value="3" class="wide"/>
```

---

### Planets (`_planetCount` through `generateAllPlanets`, lines 363–455)

Direct port of `planets.py`. Planet count is Poisson-distributed around an
expected value that depends on stellar mass and metallicity. Orbital distances
use the same geometric spacing (Titius-Bode-like), planet mass is log-uniform
split by the snow line, type is mass+snow-line classification, radius is
Chen-Kipping.

```js
function _planetCount(star, rng) {
  const m = star.mass;
  let e = m < 0.6 ? 5 : m < 1.0 ? 4 : m < 1.5 ? 3.5 : 3.0;
  e *= 0.75 + 0.5*star.metallicity;
  return Math.max(1, Math.min(rng.poisson(e), 10));
}

function _snowLine(star) { return 2.7 * Math.sqrt(star.luminosity); }

function _orbitalDistances(count, star, rng, cfg) {
  if (count === 1) return [rng.uniform(cfg.minOrbitalDistance, cfg.maxOrbitalDistance)];
  const d = [rng.uniform(cfg.minOrbitalDistance, Math.min(0.5, cfg.maxOrbitalDistance))];
  const ratio = rng.uniform(1.5, 2.5);
  for (let i = 1; i < count; i++) {
    const nx = d[d.length-1] * ratio;
    if (nx > cfg.maxOrbitalDistance) break;
    d.push(nx);
  }
  return d;
}
```

Equilibrium temperature is the same radiative balance formula:
```js
function _planetTemp(lum, od, albedo) {
  return 278.5 * Math.pow(lum, 0.25) * Math.pow(1-albedo, 0.25) / Math.sqrt(od);
}
```

---

### The generation entry point (`generateUniverse`, lines 457–464)

```js
function generateUniverse(cfg) {
  const rng     = makePRNG(cfg.seed);
  const lattice = generateLattice(cfg);
  const systems = generateSystems(lattice, rng, cfg);
  const stars   = generateStars(rng, systems, cfg);
  const planets = generateAllPlanets(stars, rng, cfg);
  return {systems, stars, planets, moons: [], seed: cfg.seed};
}
```

The lattice doesn't use the RNG — it only uses Perlin noise seeded by
`cfg.seed` offsets. The RNG is used for everything after: which candidate cells
get systems, how many stars, which mass they get, how many planets, etc.

---

## Layer 2 — Viewer

The viewer is all inside `initViewer(DATA)` (lines 489–872). It takes the
generated data and builds a three.js scene.

### Visual scale constants (line 492)

```js
const AU     = 6.0;   // world units per AU — scales orbital distances
const MOON   = 150.0; // world units per AU for moon orbits
const GAP    = 0.45;  // minimum gap between bodies in the system view
```

`AU` is the most useful one to change. Increasing it spreads planets further
apart in the system view; decreasing it compresses them together.

### Body size functions (lines 493–494)

```js
const starVR   = r => Math.max(0.30, Math.min(0.80, 0.35*r));
const planetVR = r => Math.max(0.12, Math.min(0.60, 0.22*Math.sqrt(Math.max(0.01,r))));
```

`starVR` maps a solar-radius value to a visual radius in world units, clamped
to [0.30, 0.80]. `planetVR` does the same for Earth radii with a square root
to keep giant planets from dominating the view. Tweak the multipliers (0.35,
0.22) or the clamp limits to change how big bodies look.

### Colours (lines 577–579)

```js
function metColor(m) {
  return new THREE.Color(0x3a6bff).lerp(new THREE.Color(0xff9b3a), Math.max(0, Math.min(1, m)));
}
const SPEC_COL = {O:'#9bb0ff', B:'#aabfff', A:'#cad7ff', F:'#f8f7ff', G:'#fff4e8', K:'#ffd2a1', M:'#ffcc6f'};
const PL_COL   = {terrestrial:0x4caf50, ice_giant:0x64b5f6, gas_giant:0xff7043};
```

`metColor` linearly interpolates between blue (metallicity=0) and orange
(metallicity=1). Change the two hex values to change what low/high metallicity
looks like. `SPEC_COL` and `PL_COL` control star and planet colours directly
by type.

### System view — orbit layout (lines 661–668)

The orbits aren't drawn at their physical AU distances. Instead each planet is
given the maximum of its physical distance and enough space to not overlap with
the previous planet:

```js
pl.forEach(p => {
  const rp = planetVR(p.radius), sr = starRadius[p.star_id] || maxStarR;
  let a = Math.max(p.orbital_distance * AU, 1.25*sr + rp + GAP);
  if (stars.length > 1) a = Math.max(a, sep + sr + rp + GAP);
  if (prevA !== null)   a = Math.max(a, prevA + prevR + rp + GAP);
  orbits.push(a); prevA = a; prevR = rp;
});
```

This means the visual layout is readable but not physically accurate. If you
want physically accurate distances (where inner planets crowd together), remove
the `prevA` check and just use `p.orbital_distance * AU` directly.

### Background starfield (lines 551–566)

```js
const srng = makePRNG(DATA.seed + 99);
mkLayer(3500, 0.75, 1.0, 0x8899bb, 1.0, 0.55); // faint distant stars
mkLayer( 700, 0.60, 0.8, 0xddeeff, 1.8, 0.85); // brighter foreground stars
```

It uses a separate RNG seeded at `seed + 99` so the background doesn't
reshuffle when you regenerate with a different seed (it will change with seed
but won't change just because of different generation parameters).

---

## Layer 3 — UI

### Config form and regeneration (lines 895–944)

`readCfg()` reads every input field and returns a config object. `runGeneration(cfg)`
calls `generateUniverse(cfg)` and then `initViewer(data)`. The loading screen
is shown first; `requestAnimationFrame` is used twice to let the browser paint
it before the blocking computation starts.

```js
function runGeneration(cfg) {
  document.getElementById('loading').style.display = 'flex';
  requestAnimationFrame(() => requestAnimationFrame(() => {
    const data = generateUniverse(cfg);
    initViewer(data);
    // ...
    document.getElementById('loading').style.display = 'none';
  }));
}

// Initial generation on page load
runGeneration(readCfg());
```

All the initial values come from the HTML input `value` attributes. Changing
those changes the default universe.

### Filter panel (lines 809–831)

The filter runs entirely client-side over the already-generated data. It
doesn't regenerate anything — it just calls `buildSystems(visible)` with a
filtered list.

```js
function applyFilter() {
  const visible = systems.filter(s => {
    if (s.metallicity < metMin || s.metallicity > metMax) return false;
    if ((planetCount[s.id] || 0) < minP) return false;
    // spectral type check only if not all types are selected
    if (specs.length < SPECS.length) {
      const sp = (starsBySys[s.id] || []).map(st => st.spectral_type);
      if (!sp.some(x => specs.includes(x))) return false;
    }
    return true;
  });
  buildSystems(visible);
}
```

---

## Common things to change

**Different default universe:** change `value="125"` on the seed input.

**More planets per star:** increase the expected values in `_planetCount`:
```js
let e = m < 0.6 ? 5 : m < 1.0 ? 4 : m < 1.5 ? 3.5 : 3.0;
```

**More systems:** lower the density threshold default from `value="0.5"`, or
raise the lattice resolution from `value="50"` (warning: lattice generation
time scales as N³).

**Different planet colours:** edit `PL_COL`:
```js
const PL_COL = {terrestrial: 0x4caf50, ice_giant: 0x64b5f6, gas_giant: 0xff7043};
```

**Planets further apart in system view:** increase `AU` from 6.0.

**Stars look too small or too big:** adjust the multiplier in `starVR`:
```js
const starVR = r => Math.max(0.30, Math.min(0.80, 0.35*r));
//                                                 ^^^^ change this
```
