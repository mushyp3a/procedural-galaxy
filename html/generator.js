'use strict';

// random numbers, same seed = same galaxy
function makePRNG(seed) {
  let s = (seed | 0) >>> 0 || 1;
  function next() {
    s ^= s << 13;
    s ^= s >>> 17;
    s ^= s << 5;
    return (s >>> 0) / 4294967296;
  }
  return {
    next,
    // random number between a and b
    uniform(a, b) {
      return a + next() * (b - a);
    },
    int(lo, hi) {
      return lo + ((next() * (hi - lo)) | 0);
    },
    shuffle(arr) {
      for (let i = arr.length - 1; i > 0; i--) {
        const j = (next() * (i + 1)) | 0;
        const t = arr[i];
        arr[i] = arr[j];
        arr[j] = t;
      }
    },
    // poisson, averages around lam
    // bigger lam = more spread
    poisson(lam) {
      if (lam <= 0) return 0;
      const L = Math.exp(-Math.min(lam, 500));
      let k = 0,
        p = 1;
      do {
        k++;
        p *= next();
      } while (p > L && k < 200);
      return k - 1;
    },
  };
}

// perlin table (copied from the original paper)
const _PBASE = [
  151, 160, 137, 91, 90, 15, 131, 13, 201, 95, 96, 53, 194, 233, 7, 225, 140, 36, 103, 30, 69, 142,
  8, 99, 37, 240, 21, 10, 23, 190, 6, 148, 247, 120, 234, 75, 0, 26, 197, 62, 94, 252, 219, 203,
  117, 35, 11, 32, 57, 177, 33, 88, 237, 149, 56, 87, 174, 20, 125, 136, 171, 168, 68, 175, 74, 165,
  71, 134, 139, 48, 27, 166, 77, 146, 158, 231, 83, 111, 229, 122, 60, 211, 133, 230, 220, 105, 92,
  41, 55, 46, 245, 40, 244, 102, 143, 54, 65, 25, 63, 161, 1, 216, 80, 73, 209, 76, 132, 187, 208,
  89, 18, 169, 200, 196, 135, 130, 116, 188, 159, 86, 164, 100, 109, 198, 173, 186, 3, 64, 52, 217,
  226, 250, 124, 123, 5, 202, 38, 147, 118, 126, 255, 82, 85, 212, 207, 206, 59, 227, 47, 16, 58,
  17, 182, 189, 28, 42, 223, 183, 170, 213, 119, 248, 152, 2, 44, 154, 163, 70, 221, 153, 101, 155,
  167, 43, 172, 9, 129, 22, 39, 253, 19, 98, 108, 110, 79, 113, 224, 232, 178, 185, 112, 104, 218,
  246, 97, 228, 251, 34, 242, 193, 238, 210, 144, 12, 191, 179, 162, 241, 81, 51, 145, 235, 249, 14,
  239, 107, 49, 192, 214, 31, 181, 199, 106, 157, 184, 84, 204, 176, 115, 121, 50, 45, 127, 4, 150,
  254, 138, 236, 205, 93, 222, 114, 67, 29, 24, 72, 243, 141, 128, 195, 78, 66, 215, 61, 156, 180,
];

// the table twice in a row so the lookups dont overflow
const _P = new Uint8Array(512);
for (let i = 0; i < 256; i++) _P[i] = _P[i + 256] = _PBASE[i];

function _fade(t) {
  return t * t * t * (t * (t * 6 - 15) + 10);
}
// lerp, blends between a and b, t=0 is a and t=1 is b
function _lp(t, a, b) {
  return a + t * (b - a);
}
function _grad(h, x, y, z) {
  h &= 15;
  const u = h < 8 ? x : y,
    v = h < 4 ? y : h === 12 || h === 14 ? x : z;
  return (h & 1 ? -u : u) + (h & 2 ? -v : v);
}
function _raw3(x, y, z) {
  const xi = Math.floor(x) & 255,
    yi = Math.floor(y) & 255,
    zi = Math.floor(z) & 255;
  const xf = x - Math.floor(x),
    yf = y - Math.floor(y),
    zf = z - Math.floor(z);
  const u = _fade(xf),
    v = _fade(yf),
    w = _fade(zf);
  const A = _P[xi] + yi,
    B = _P[xi + 1] + yi;
  const AA = _P[A] + zi,
    AB = _P[A + 1] + zi,
    BA = _P[B] + zi,
    BB = _P[B + 1] + zi;
  return _lp(
    w,
    _lp(
      v,
      _lp(u, _grad(_P[AA], xf, yf, zf), _grad(_P[BA], xf - 1, yf, zf)),
      _lp(u, _grad(_P[AB], xf, yf - 1, zf), _grad(_P[BB], xf - 1, yf - 1, zf)),
    ),
    _lp(
      v,
      _lp(u, _grad(_P[AA + 1], xf, yf, zf - 1), _grad(_P[BA + 1], xf - 1, yf, zf - 1)),
      _lp(u, _grad(_P[AB + 1], xf, yf - 1, zf - 1), _grad(_P[BB + 1], xf - 1, yf - 1, zf - 1)),
    ),
  );
}
function perlin01(x, y, z, base, octaves) {
  let val = 0,
    amp = 1,
    freq = 1,
    maxA = 0;
  for (let o = 0; o < octaves; o++) {
    val += _raw3(x * freq + base, y * freq + base, z * freq + base) * amp;
    maxA += amp;
    amp *= 0.5;
    freq *= 2;
  }
  return (val / maxA + 1) * 0.5;
}

function generateLattice(cfg) {
  const { seed, clusterScale, elementOctaves, latticeResolution: N } = cfg;
  const steps = new Float64Array(N);
  for (let i = 0; i < N; i++) steps[i] = Math.round((i / (N - 1)) * clusterScale * 100) / 100;

  const size = N * N * N;
  const density = new Float32Array(size),
    H = new Float32Array(size),
    He = new Float32Array(size),
    C = new Float32Array(size),
    O = new Float32Array(size),
    met = new Float32Array(size);

  for (let zi = 0; zi < N; zi++)
    for (let yi = 0; yi < N; yi++)
      for (let xi = 0; xi < N; xi++) {
        const idx = zi * N * N + yi * N + xi;
        const sx = steps[xi],
          sy = steps[yi],
          sz = steps[zi];
        const d = perlin01(sx, sy, sz, seed + 6, elementOctaves);
        density[idx] = d;
        C[idx] = perlin01(sx, sy, sz, seed + 1, elementOctaves) * d;
        O[idx] = perlin01(sx, sy, sz, seed + 2, elementOctaves) * d;
        He[idx] = perlin01(sx, sy, sz, seed + 3, elementOctaves) * d;
        H[idx] = perlin01(sx, sy, sz, seed + 4, elementOctaves) * d;
        met[idx] = perlin01(sx, sy, sz, seed + 5, elementOctaves);
      }
  return { density, H, He, C, O, met, N, steps };
}

// puts a system in the grid cells that are dense enough
function generateSystems(lattice, rng, cfg) {
  const { density, H, He, C, O, met, N } = lattice;
  const { densityThreshold, HThreshold, HeThreshold } = cfg;
  const universeSize = 1000;
  const cellSize = universeSize / N;

  const candidates = [];
  for (let idx = 0; idx < N * N * N; idx++) {
    if (density[idx] <= densityThreshold) continue;
    if (H[idx] <= HThreshold) continue;
    if (He[idx] <= HeThreshold) continue;
    candidates.push(idx);
  }
  rng.shuffle(candidates);

  const systems = [];
  for (const idx of candidates) {
    if (rng.next() > density[idx] * H[idx] * He[idx]) continue;
    const zi = (idx / (N * N)) | 0,
      rem = idx % (N * N),
      yi = (rem / N) | 0,
      xi = rem % N;
    const maxOff = cellSize * 0.4;
    systems.push({
      id: systems.length + 1,
      x: xi * cellSize + rng.uniform(-maxOff, maxOff),
      y: yi * cellSize + rng.uniform(-maxOff, maxOff),
      z: zi * cellSize + rng.uniform(-maxOff, maxOff),
      density: density[idx],
      H: H[idx],
      He: He[idx],
      C: C[idx],
      O: O[idx],
      metallicity: met[idx],
    });
  }
  return systems;
}

// maths for picking numbers from a power law
function _powerLawIntegral(lo, hi, alpha) {
  if (alpha === 1) return Math.log(hi / lo);
  const e = 1 - alpha;
  return (Math.pow(hi, e) - Math.pow(lo, e)) / e;
}

function _samplePL(rng, lo, hi, alpha) {
  const e = 1 - alpha;
  return Math.pow(Math.pow(lo, e) + rng.next() * (Math.pow(hi, e) - Math.pow(lo, e)), 1 / e);
}

function _starMass(rng) {
  const lW = _powerLawIntegral(0.179, 0.5, 1.3);
  const hW = Math.pow(0.5, 2.3 - 1.3) * _powerLawIntegral(0.5, 31.0, 2.3);
  return rng.next() < lW / (lW + hW)
    ? _samplePL(rng, 0.179, 0.5, 1.3)
    : _samplePL(rng, 0.5, 31.0, 2.3);
}

function _starLuminosity(m) {
  const lm = Math.log10(m);
  if (m <= 0.45) return Math.pow(10, 2.028 * lm - 0.976);
  if (m <= 0.72) return Math.pow(10, 4.572 * lm - 0.102);
  if (m <= 1.05) return Math.pow(10, 5.743 * lm - 0.007);
  if (m <= 2.4) return Math.pow(10, 4.329 * lm + 0.01);
  if (m <= 7.0) return Math.pow(10, 3.967 * lm + 0.093);
  return Math.pow(10, 2.865 * lm + 1.105);
}

function _starTemperature(mass, luminosity, radius) {
  if (mass > 1.5) {
    const lm = Math.log10(mass);
    return Math.pow(10, -0.17 * lm * lm + 0.888 * lm + 3.671);
  }
  return 5772 * Math.pow(luminosity / (radius * radius), 0.25);
}

function _starRadius(mass, luminosity) {
  if (mass <= 1.5) return 0.438 * mass * mass + 0.479 * mass + 0.075;
  const temp = _starTemperature(mass);
  return Math.sqrt(luminosity / Math.pow(temp / 5772, 4));
}

// turns temperature into a letter like g or k
function _starSpectralType(t) {
  if (t >= 30000) return 'O';
  if (t >= 10000) return 'B';
  if (t >= 7500) return 'A';
  if (t >= 6000) return 'F';
  if (t >= 5200) return 'G';
  if (t >= 3700) return 'K';
  return 'M';
}

function _generateStar(rng, system) {
  const mass = _starMass(rng);
  const luminosity = _starLuminosity(mass);
  let radius, temperature;
  if (mass <= 1.5) {
    radius = _starRadius(mass, luminosity);
    temperature = _starTemperature(mass, luminosity, radius);
  } else {
    temperature = _starTemperature(mass);
    radius = _starRadius(mass, luminosity);
  }
  return {
    mass,
    luminosity,
    radius,
    temperature,
    spectral_type: _starSpectralType(temperature),
    metallicity: system.metallicity,
  };
}

function generateStars(rng, systems, cfg) {
  const stars = [];
  for (let si = 0; si < systems.length; si++) {
    const sys = systems[si];
    const n = rng.int(1, cfg.maxStarsPerSystem + 1);
    for (let sn = 0; sn < n; sn++) {
      const s = _generateStar(rng, sys);
      stars.push({
        id: stars.length + 1,
        system_id: sys.id,
        star_number: sn,
        mass: s.mass,
        luminosity: s.luminosity,
        radius: s.radius,
        temperature: s.temperature,
        spectral_type: s.spectral_type,
        metallicity: s.metallicity,
      });
    }
  }
  return stars;
}

function _planetCount(star, rng) {
  const m = star.mass;
  let e = m < 0.6 ? 5 : m < 1.0 ? 4 : m < 1.5 ? 3.5 : 3.0;
  e *= 0.75 + 0.5 * star.metallicity;
  return Math.max(1, Math.min(rng.poisson(e), 10));
}

// distance where ice can form
function _snowLine(star) {
  return 2.7 * Math.sqrt(star.luminosity);
}

function _orbitalDistances(count, star, rng, cfg) {
  const mn = cfg.minOrbitalDistance,
    mx = cfg.maxOrbitalDistance;
  if (count === 1) return [rng.uniform(mn, mx)];
  const d = [rng.uniform(mn, Math.min(0.5, mx))];
  const ratio = rng.uniform(1.5, 2.5);
  for (let i = 1; i < count; i++) {
    const nx = d[d.length - 1] * ratio;
    if (nx > mx) break;
    d.push(nx);
  }
  return d;
}

function _planetMass(star, od, rng) {
  const snow = _snowLine(star);
  const mf = 0.6 + 0.8 * star.metallicity;
  const mn = od < snow ? 0.1 : 1.0;
  const mx = od < snow ? 10.0 : 4000.0;
  const raw = Math.pow(10, rng.uniform(Math.log10(mn), Math.log10(mx)));
  return Math.max(0.1, Math.min(raw * mf, 4000));
}

// terrestrial, ice giant or gas giant
function _planetType(mass, od, star) {
  const snow = _snowLine(star);
  if (mass < 10) return 'terrestrial';
  if (od >= snow && mass < 100) return 'ice_giant';
  return 'gas_giant';
}

function _planetRadius(mass) {
  if (mass < 2.04) return 1.008 * Math.pow(mass, 0.279);
  if (mass < 132) return 1.008 * Math.pow(mass, 0.589);
  return 11 * Math.pow(mass, -0.044);
}

// how much light the planet reflects
function _albedo(type, rng) {
  if (type === 'terrestrial') return rng.uniform(0.1, 0.6);
  if (type === 'ice_giant') return rng.uniform(0.2, 0.7);
  return rng.uniform(0.2, 0.6);
}

function _planetTemp(lum, od, albedo) {
  return (278.5 * Math.pow(lum, 0.25) * Math.pow(1 - albedo, 0.25)) / Math.sqrt(od);
}

function _generatePlanet(star, orbitalOrder, od, rng) {
  const mass = _planetMass(star, od, rng);
  const type = _planetType(mass, od, star);
  const radius = _planetRadius(mass);
  const albedo = _albedo(type, rng);
  const temp = _planetTemp(star.luminosity, od, albedo);
  return {
    orbital_order: orbitalOrder,
    orbital_distance: od,
    mass,
    radius,
    planet_type: type,
    albedo,
    temperature: temp,
  };
}

function _generatePlanets(star, rng, cfg) {
  const count = _planetCount(star, rng);
  const dists = _orbitalDistances(count, star, rng, cfg);
  const planets = [];
  for (let i = 0; i < dists.length; i++) planets.push(_generatePlanet(star, i + 1, dists[i], rng));
  return planets;
}

function generateAllPlanets(stars, rng, cfg) {
  const planets = [];
  let pid = 1;
  for (const star of stars) {
    for (const p of _generatePlanets(star, rng, cfg)) {
      planets.push({ id: pid++, system_id: star.system_id, star_id: star.id, ...p });
    }
  }
  return planets;
}

function _moonCount(planet, rng) {
  const lam =
    planet.planet_type === 'gas_giant' ? 5 : planet.planet_type === 'ice_giant' ? 2 : 0.15;
  return Math.min(rng.poisson(lam), 12);
}

function _moonMass(planet, rng) {
  return planet.mass * Math.pow(10, rng.uniform(-5, Math.log10(0.02)));
}

function _moonRadius(mass) {
  return 1.008 * Math.pow(Math.max(mass, 1e-6), 0.279);
}

// rocky or icy moon
function _moonType(moonOD, planet, star) {
  return planet.orbital_distance > _snowLine(star) ? 'icy' : 'rocky';
}

function _moonOrbitalDistances(planet, star, count, rng) {
  if (count === 0) return [];
  const roche = 2.5 * planet.radius * 4.26e-5;
  // same sizes as the viewer uses
  const pvr = Math.max(0.12, Math.min(0.6, 0.22 * Math.sqrt(Math.max(0.01, planet.radius))));
  const minD = Math.max(roche, (pvr + 0.5) / 150);
  const hill =
    0.5 * planet.orbital_distance * Math.pow(planet.mass / (3 * star.mass * 333000), 1 / 3);
  const maxD = Math.min(hill, minD * 60);
  if (maxD <= minD) return [];
  const dists = [];
  let d = minD * rng.uniform(1.0, 2.0);
  const ratio = rng.uniform(1.8, 3.2);
  for (let i = 0; i < count && d <= maxD; i++) {
    dists.push(d);
    d *= ratio * rng.uniform(0.8, 1.2);
  }
  return dists;
}

function _generateMoons(planet, star, rng) {
  const count = _moonCount(planet, rng);
  const dists = _moonOrbitalDistances(planet, star, count, rng);
  return dists.map((od, i) => {
    const mass = _moonMass(planet, rng);
    return {
      orbital_order: i + 1,
      orbital_distance: od,
      mass,
      radius: _moonRadius(mass),
      moon_type: _moonType(od, planet, star),
    };
  });
}

function generateAllMoons(planets, starsById, rng) {
  const moons = [];
  let mid = 1;
  for (const planet of planets) {
    const star = starsById[planet.star_id];
    if (!star) continue;
    for (const m of _generateMoons(planet, star, rng))
      moons.push({
        id: mid++,
        planet_id: planet.id,
        star_id: planet.star_id,
        system_id: planet.system_id,
        ...m,
      });
  }
  return moons;
}

function generateUniverse(cfg) {
  const rng = makePRNG(cfg.seed);
  const lattice = generateLattice(cfg);
  const systems = generateSystems(lattice, rng, cfg);
  const stars = generateStars(rng, systems, cfg);
  const planets = generateAllPlanets(stars, rng, cfg);
  const starsById = Object.fromEntries(stars.map((s) => [s.id, s]));
  const moons = generateAllMoons(planets, starsById, rng);
  return { systems, stars, planets, moons, seed: cfg.seed };
}
