#!/usr/bin/env python3

# turns universe.db into explore.html, a 3d viewer you can open in the browser
# run universe.py first to make the database, then this


import sqlite3
import json
import os

DB_PATH = "universe.db"
OUT_PATH = "explore.html"

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


def collect(db_path):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    systems = [
        dict(r)
        for r in conn.execute(
            "SELECT id, x, y, z, density, H, He, C, O, metallicity FROM systems"
        )
    ]
    stars = [
        dict(r)
        for r in conn.execute(
            "SELECT id, system_id, star_number, mass, radius, temperature, "
            "luminosity, metallicity, spectral_type FROM stars"
        )
    ]
    planets = [
        dict(r)
        for r in conn.execute(
            "SELECT id, system_id, star_id, orbital_order, orbital_distance, "
            "mass, radius, temperature, planet_type, albedo FROM planets"
        )
    ]
    moons = [
        dict(r)
        for r in conn.execute(
            "SELECT id, planet_id, orbital_order, orbital_distance, "
            "mass, radius FROM moons"
        )
    ]
    conn.close()
    return {
        "systems": systems,
        "stars": stars,
        "planets": planets,
        "moons": moons,
    }


HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>Procedural Universe Explorer</title>
<style>
  html,body{margin:0;height:100%;background:#05060a;color:#cfe3ff;
    font-family:ui-monospace,Menlo,Consolas,monospace;overflow:hidden}
  #container{position:fixed;inset:0}
  .panel{position:fixed;background:rgba(10,14,24,0.82);border:1px solid #1d2a44;
    border-radius:8px;padding:10px 12px;backdrop-filter:blur(4px);font-size:12px;line-height:1.5}
  #info{top:12px;right:12px;width:280px;max-height:72vh;overflow:auto}
  #search{top:12px;left:12px;width:236px;max-height:90vh;overflow:auto}
  #breadcrumb{bottom:12px;left:12px}
  #legend{bottom:12px;right:12px;width:200px}
  #controls{bottom:12px;left:260px;width:232px}
  #tooltip{position:fixed;display:none;pointer-events:none;background:rgba(10,14,24,0.9);
    border:1px solid #2a4a7a;border-radius:6px;padding:4px 7px;font-size:11px;color:#cfe3ff;z-index:10}
  h3{margin:0 0 6px;font-size:13px;color:#9fd0ff}
  table{border-collapse:collapse;width:100%}
  td{padding:1px 4px;vertical-align:top}
  td.k{color:#7f9bc4;width:44%}
  input[type=number],input[type=text]{width:78px;background:#0b1120;color:#cfe3ff;
    border:1px solid #1d2a44;border-radius:4px;padding:2px 4px}
  button{background:#16335c;color:#cfe3ff;border:1px solid #2a4a7a;border-radius:4px;
    padding:3px 8px;cursor:pointer;font-family:inherit}
  button:hover{background:#1d447d}
  .sw{display:inline-block;width:10px;height:10px;border-radius:50%;margin-right:5px;vertical-align:middle}
  #matchList{margin-top:6px;max-height:200px;overflow:auto}
  #matchList div{cursor:pointer;padding:1px 3px;border-radius:3px}
  #matchList div:hover{background:#16335c}
  label{display:inline-block;margin:1px 4px 1px 0}
  .row{display:flex;gap:6px;align-items:center;margin:3px 0;flex-wrap:wrap}
</style>
</head>
<body>
<div id="container"></div>
<div id="tooltip"></div>

<div id="search" class="panel">
  <h3>Search / Filter</h3>
  <div class="row"><input id="sysId" type="text" placeholder="system id"/><button id="goId">Go</button></div>
  <div class="row"><span>Met min</span><input id="metMin" type="number" step="0.05" min="0" max="1" value="0"/></div>
  <div class="row"><span>Met max</span><input id="metMax" type="number" step="0.05" min="0" max="1" value="1"/></div>
  <div class="row"><span>Min planets</span><input id="minP" type="number" min="0" max="20" value="0"/></div>
  <div class="row"><span>Spectral</span><span id="specBoxes"></span></div>
  <div class="row"><button id="applyF">Apply</button><span id="matchCount"></span></div>
  <div id="matchList"></div>
</div>

<div id="info" class="panel">Click a system to explore.</div>

<div id="breadcrumb" class="panel"><span id="crumb">Universe</span> <button id="backBtn" style="display:none">&#8592; Back to universe</button></div>

<div id="controls" class="panel">
  <h3>Controls</h3>
  <div><b>WASD</b>: move &middot; <b>Shift</b>: boost</div>
  <div><b>Space</b>: up &middot; <b>Ctrl</b>: down</div>
  <div>Left-drag: rotate</div>
  <div>Right-drag / two-finger: pan</div>
  <div>Wheel: zoom</div>
  <div>Click a system (or a Search result) to fly in</div>
  <div><b>Esc</b>: back to universe</div>
</div>

<div id="legend" class="panel">
  <h3>Legend</h3>
  <div><span class="sw" style="background:#3a6bff"></span>low metallicity</div>
  <div><span class="sw" style="background:#ff9b3a"></span>high metallicity</div>
  <div style="margin-top:4px"><span class="sw" style="background:#4caf50"></span>terrestrial</div>
  <div><span class="sw" style="background:#64b5f6"></span>ice giant</div>
  <div><span class="sw" style="background:#ff7043"></span>gas giant</div>
  <div style="margin-top:4px">Lines = star&rarr;planet&rarr;moon</div>
</div>

<script src="./viewer/three.min.js"></script>
<script src="./viewer/OrbitControls.js"></script>
<script>
const DATA = ___DATA___;

(function () {
  'use strict';

  // ---- tunables (visual scales, not physical) ----
  const AU = 6.0;        // world units per AU for planet orbits
  const MOON = 150.0;    // world units per AU for moon orbits
  const STAR_SEP = 1.5;  // separation of stars in a multi-star system (recomputed below)
  const GAP = 0.45;      // min gap between bodies so they never overlap (incl. glow halos)
  // Compressed, minimalist visual radii (real mass-derived, but bounded).
  const starVR = r => Math.max(0.30, Math.min(0.80, 0.35 * r));       // solar radii
  const planetVR = r => Math.max(0.12, Math.min(0.60, 0.22 * Math.sqrt(Math.max(0.01, r)))); // Earth radii

  let mode = 'universe', currentSys = null;
  let systemPoints = null, systemOrder = [];

  // ---- indices ----
  const systems = DATA.systems;
  const starsBySys = {}, planetsBySys = {}, moonsByPlanet = {}, sysById = {};
  const planetCount = {};
  systems.forEach(s => { sysById[s.id] = s; planetCount[s.id] = 0; });
  DATA.stars.forEach(s => { (starsBySys[s.system_id] = starsBySys[s.system_id] || []).push(s); });
  DATA.planets.forEach(p => {
    (planetsBySys[p.system_id] = planetsBySys[p.system_id] || []).push(p);
    planetCount[p.system_id] = (planetCount[p.system_id] || 0) + 1;
  });
  DATA.moons.forEach(m => { (moonsByPlanet[m.planet_id] = moonsByPlanet[m.planet_id] || []).push(m); });

  // ---- renderer / scene ----
  const container = document.getElementById('container');
  const scene = new THREE.Scene();
  scene.background = new THREE.Color(0x05060a);
  const camera = new THREE.PerspectiveCamera(60, innerWidth / innerHeight, 0.1, 40000);
  const renderer = new THREE.WebGLRenderer({ antialias: true });
  renderer.setPixelRatio(devicePixelRatio);
  renderer.setSize(innerWidth, innerHeight);
  container.appendChild(renderer.domElement);
  const controls = new THREE.OrbitControls(camera, renderer.domElement);
  controls.enableDamping = true;
  controls.dampingFactor = 0.08;
  controls.screenSpacePanning = true;

  // camera fly-to targets
  const desiredTarget = new THREE.Vector3(500, 500, 500);
  const desiredCam = new THREE.Vector3(500, 300, 1500);
  camera.position.copy(desiredCam);
  controls.target.copy(desiredTarget);

  let flying = false;
  function startFlight(camPos, target) {
    desiredCam.copy(camPos);
    desiredTarget.copy(target);
    flying = true;
    controls.enabled = false;
  }
  function cancelFlight() {
    if (flying) { flying = false; controls.enabled = true; }
  }
  renderer.domElement.addEventListener('pointerdown', cancelFlight);
  renderer.domElement.addEventListener('wheel', cancelFlight, { passive: true });

  // ---- free-fly keys (WASD + Shift boost, Space up, Ctrl down) ----
  const UP = new THREE.Vector3(0, 1, 0);
  const FLY_SLOW = 150, FLY_FAST = 700; // world units / second
  const clock = new THREE.Clock();
  const keys = {};
  function typing() { return document.activeElement && /INPUT|TEXTAREA/.test(document.activeElement.tagName); }
  addEventListener('keydown', e => {
    if (typing()) return;            // don't capture while using the Search box
    keys[e.code] = true;
    if (e.code === 'Space') e.preventDefault(); // stop page scroll
  });
  addEventListener('keyup', e => { keys[e.code] = false; });

  // ---- starfield ----
  (function () {
    const N = 4000, pos = new Float32Array(N * 3);
    for (let i = 0; i < N; i++) {
      const r = 3000 + Math.random() * 5000;
      const t = Math.random() * Math.PI * 2, ph = Math.acos(2 * Math.random() - 1);
      pos[i * 3] = r * Math.sin(ph) * Math.cos(t);
      pos[i * 3 + 1] = r * Math.cos(ph);
      pos[i * 3 + 2] = r * Math.sin(ph) * Math.sin(t);
    }
    const g = new THREE.BufferGeometry();
    g.setAttribute('position', new THREE.BufferAttribute(pos, 3));
    const m = new THREE.PointsMaterial({ color: 0x8899bb, size: 1.2, sizeAttenuation: false, transparent: true, opacity: 0.7 });
    scene.add(new THREE.Points(g, m));
  })();

  function discTexture() {
    const c = document.createElement('canvas'); c.width = c.height = 64;
    const x = c.getContext('2d');
    const g = x.createRadialGradient(32, 32, 0, 32, 32, 32);
    g.addColorStop(0, 'rgba(255,255,255,1)');
    g.addColorStop(0.4, 'rgba(255,255,255,0.6)');
    g.addColorStop(1, 'rgba(255,255,255,0)');
    x.fillStyle = g; x.fillRect(0, 0, 64, 64);
    return new THREE.CanvasTexture(c);
  }
  const disc = discTexture();

  // hover tooltip (universe view) — no glow sprite, just a label
  const tooltip = document.getElementById('tooltip');

  function metColor(m) {
    const t = Math.max(0, Math.min(1, m));
    return new THREE.Color(0x3a6bff).lerp(new THREE.Color(0xff9b3a), t);
  }
  const SPEC_COL = { O: '#9bb0ff', B: '#aabfff', A: '#cad7ff', F: '#f8f7ff', G: '#fff4e8', K: '#ffd2a1', M: '#ffcc6f' };
  const PL_COL = { terrestrial: 0x4caf50, ice_giant: 0x64b5f6, gas_giant: 0xff7043 };

  // ---- systems (universe view) ----
  function buildSystems(list) {
    systemOrder = list.map(s => s.id);
    const pos = new Float32Array(list.length * 3), col = new Float32Array(list.length * 3);
    list.forEach((s, i) => {
      pos[i * 3] = s.x; pos[i * 3 + 1] = s.y; pos[i * 3 + 2] = s.z;
      const c = metColor(s.metallicity);
      col[i * 3] = c.r; col[i * 3 + 1] = c.g; col[i * 3 + 2] = c.b;
    });
    const g = new THREE.BufferGeometry();
    g.setAttribute('position', new THREE.BufferAttribute(pos, 3));
    g.setAttribute('color', new THREE.BufferAttribute(col, 3));
    if (systemPoints) { scene.remove(systemPoints); systemPoints.geometry.dispose(); systemPoints.material.dispose(); }
    // Distance-clamped point size: ~6px at overview, grows only marginally when
    // the camera is close (clamped), making dots easier to click without glare.
    const m = new THREE.ShaderMaterial({
      uniforms: { uRef: { value: 1500.0 }, uMin: { value: 3.0 }, uMax: { value: 16.0 }, uOpacity: { value: 1.0 } },
      vertexShader: [
        'attribute vec3 color;',
        'varying vec3 vColor;',
        'uniform float uRef, uMin, uMax;',
        'void main() {',
        '  vColor = color;',
        '  vec4 mv = modelViewMatrix * vec4(position, 1.0);',
        '  float d = max(1.0, -mv.z);',
        '  gl_PointSize = clamp(6.0 * (uRef / d), uMin, uMax);',
        '  gl_Position = projectionMatrix * mv;',
        '}'
      ].join('\n'),
      fragmentShader: [
        'varying vec3 vColor;',
        'uniform float uOpacity;',
        'void main() {',
        '  vec2 c = gl_PointCoord - 0.5;',
        '  if (dot(c, c) > 0.25) discard;',
        '  gl_FragColor = vec4(vColor, uOpacity);',
        '}'
      ].join('\n'),
      transparent: true,
      depthWrite: false
    });
    systemPoints = new THREE.Points(g, m);
    systemPoints.frustumCulled = false; // we scale/offset it when entering a system
    scene.add(systemPoints);
  }

  // ---- detail (system view) ----
  let detailGroup = null;
  function clearDetail() { if (detailGroup) { scene.remove(detailGroup); detailGroup = null; } }

  function rngFor(seed) {
    let s = (seed >>> 0) || 1;
    return () => { s ^= s << 13; s ^= s >>> 17; s ^= s << 5; return (s >>> 0) / 4294967296; };
  }
  function orbitPoint(a, phase, incl) {
    return new THREE.Vector3(a * Math.cos(phase), a * Math.sin(phase) * Math.cos(incl), a * Math.sin(phase) * Math.sin(incl));
  }
  function orbitRing(center, a, incl, n) {
    const pts = [];
    for (let i = 0; i <= n; i++) {
      const th = i / n * Math.PI * 2;
      pts.push(new THREE.Vector3(center.x + a * Math.cos(th), center.y + a * Math.sin(th) * Math.cos(incl), center.z + a * Math.sin(th) * Math.sin(incl)));
    }
    return new THREE.Line(new THREE.BufferGeometry().setFromPoints(pts), new THREE.LineBasicMaterial({ color: 0x4466aa, transparent: true, opacity: 0.3 }));
  }
  function edge(a, b, color) {
    return new THREE.Line(new THREE.BufferGeometry().setFromPoints([a, b]), new THREE.LineBasicMaterial({ color: color, transparent: true, opacity: 0.35 }));
  }
  function glowSprite(color, scale) {
    const m = new THREE.SpriteMaterial({ map: disc, color: color, transparent: true, opacity: 0.18, depthWrite: false, blending: THREE.AdditiveBlending });
    const sp = new THREE.Sprite(m); sp.scale.set(scale, scale, scale); return sp;
  }

  function enterSystem(sysId) {
    const sys = sysById[sysId]; if (!sys) return;
    mode = 'system'; currentSys = sysId; clearDetail();
    const center = new THREE.Vector3(sys.x, sys.y, sys.z);
    detailGroup = new THREE.Group(); scene.add(detailGroup);
    const stars = starsBySys[sysId] || [];
    const starPos = {}, starRadius = {};
    let maxStarR = 0.3;
    stars.forEach(st => { maxStarR = Math.max(maxStarR, starVR(st.radius)); });
    // Separation must clear the glow halos (sprites are scaled to r*2.5 → radius 1.25r),
    // not just the star surfaces, so sibling suns don't visually overlap.
    const starGlow = 1.25 * maxStarR;
    const sep = stars.length > 1 ? (2 * starGlow + GAP) : 0;
    const otherStarGlow = sep; // guard distance for planets orbiting one star vs its siblings
    stars.forEach((st, i) => {
      const ang = stars.length > 1 ? i / stars.length * Math.PI * 2 : 0;
      const pos = center.clone().add(new THREE.Vector3(Math.cos(ang) * sep, 0, Math.sin(ang) * sep));
      starPos[st.id] = pos;
      const r = starVR(st.radius);
      starRadius[st.id] = r;
      const col = SPEC_COL[st.spectral_type] || '#ffffff';
      const mesh = new THREE.Mesh(new THREE.SphereGeometry(r, 20, 20), new THREE.MeshBasicMaterial({ color: col }));
      mesh.position.copy(pos); mesh.userData = { type: 'star', data: st, radius: r };
      detailGroup.add(mesh);
      const gl = glowSprite(new THREE.Color(col), r * 2.5); gl.position.copy(pos); detailGroup.add(gl);
    });
    // Non-overlapping orbit layout: keep physical order/distance as a lower bound,
    // but push each orbit out so it always clears its star and the previous planet.
    const pl = (planetsBySys[sysId] || []).slice().sort((a, b) => a.orbital_distance - b.orbital_distance);
    const orbits = [];
    let prevA = null, prevR = 0;
    pl.forEach(p => {
      const rp = planetVR(p.radius);
      const sr = starRadius[p.star_id] || maxStarR;
      // Orbit must clear this star's glow (1.25·r), and in a multi-star system also
      // clear any sibling sun (so a planet never overlaps a neighbouring star).
      let a = Math.max(p.orbital_distance * AU, 1.25 * sr + rp + GAP);
      if (stars.length > 1) a = Math.max(a, otherStarGlow + sr + rp + GAP);
      if (prevA !== null) a = Math.max(a, prevA + prevR + rp + GAP);
      orbits.push(a); prevA = a; prevR = rp;
    });
    let maxOrbit = 1;
    pl.forEach((p, i) => {
      const a = orbits[i];
      const c = starPos[p.star_id] || center;
      const rand = rngFor((p.id * 2654435761) >>> 0);
      const phase = rand() * Math.PI * 2, incl = rand() * Math.PI;
      maxOrbit = Math.max(maxOrbit, a);
      const pos = c.clone().add(orbitPoint(a, phase, incl));
      const r = planetVR(p.radius);
      const mesh = new THREE.Mesh(new THREE.SphereGeometry(r, 16, 16), new THREE.MeshBasicMaterial({ color: PL_COL[p.planet_type] || 0xffffff }));
      mesh.position.copy(pos); mesh.userData = { type: 'planet', data: p, radius: r };
      detailGroup.add(mesh);
      detailGroup.add(orbitRing(c, a, incl, 80));
      detailGroup.add(edge(c, pos, 0x335588));
      (moonsByPlanet[p.id] || []).forEach(mn => {
        const mr = Math.max(0.001, mn.orbital_distance) * MOON;
        const ph2 = rand() * Math.PI * 2, ic2 = rand() * Math.PI;
        const mp = pos.clone().add(orbitPoint(mr, ph2, ic2));
        const mmesh = new THREE.Mesh(new THREE.SphereGeometry(Math.max(0.06, planetVR(mn.radius) * 0.6), 10, 10), new THREE.MeshBasicMaterial({ color: 0xcccccc }));
        mmesh.position.copy(mp); mmesh.userData = { type: 'moon', data: mn, radius: 0.1 };
        detailGroup.add(mmesh);
        detailGroup.add(orbitRing(pos, mr, ic2, 40));
        detailGroup.add(edge(pos, mp, 0x555555));
      });
    });
    const dist = Math.max(60, (maxOrbit + 1.25 * maxStarR) * 1.5);
    startFlight(center.clone().add(new THREE.Vector3(0, dist * 0.3, dist)), center);
    // Make the surrounding galaxy feel correctly scaled: pin the selected system in
    // place and blow the rest of the galaxy outward, so neighbouring systems recede to
    // a great (realistic) distance instead of floating among the planets. Keep a faint
    // opacity so distant stars remain as a subtle backdrop.
    if (systemPoints) {
      const K = 120.0;
      systemPoints.scale.setScalar(K);
      systemPoints.position.copy(center.clone().multiplyScalar(1 - K));
      systemPoints.material.uniforms.uOpacity.value = 0.0;
    }
    showSystemInfo(sys);
    document.getElementById('backBtn').style.display = 'inline-block';
    document.getElementById('crumb').textContent = 'System #' + sysId;
  }

  function exitSystem() {
    mode = 'universe'; currentSys = null; clearDetail();
    if (systemPoints) {
      systemPoints.scale.setScalar(1);
      systemPoints.position.set(0, 0, 0);
      systemPoints.material.uniforms.uOpacity.value = 1.0;
    }
    startFlight(new THREE.Vector3(500, 300, 1500), new THREE.Vector3(500, 500, 500));
    document.getElementById('info').innerHTML = 'Click a system to explore.';
    document.getElementById('backBtn').style.display = 'none';
    document.getElementById('crumb').textContent = 'Universe';
  }

  // ---- picking ----
  const ray = new THREE.Raycaster(); ray.params.Points.threshold = 12;
  const mouse = new THREE.Vector2();
  let downXY = null;

  // Pick the system whose projected screen position is nearest the cursor
  // (robust in dense point clouds, unlike a fixed ray threshold).
  function nearestSystemToCursor(mx, my) {
    const v = new THREE.Vector3(); let best = null, bestD = 18;
    for (const id of systemOrder) {
      const s = sysById[id];
      v.set(s.x, s.y, s.z).project(camera);
      if (v.z > 1) continue; // behind camera
      const sx = (v.x * 0.5 + 0.5) * innerWidth;
      const sy = (-v.y * 0.5 + 0.5) * innerHeight;
      const d = Math.hypot(sx - mx, sy - my);
      if (d < bestD) { bestD = d; best = id; }
    }
    return best;
  }

  renderer.domElement.addEventListener('pointerdown', e => { downXY = [e.clientX, e.clientY]; });
  renderer.domElement.addEventListener('pointerup', e => {
    if (!downXY) return;
    const dx = e.clientX - downXY[0], dy = e.clientY - downXY[1]; downXY = null;
    if (dx * dx + dy * dy > 25) return; // drag, not a click
    if (mode === 'universe' && systemPoints) {
      const id = nearestSystemToCursor(e.clientX, e.clientY);
      if (id != null) enterSystem(id);
    } else if (mode === 'system' && detailGroup) {
      mouse.x = (e.clientX / innerWidth) * 2 - 1;
      mouse.y = -(e.clientY / innerHeight) * 2 + 1;
      ray.setFromCamera(mouse, camera);
      const hits = ray.intersectObjects(detailGroup.children, false)
        .filter(h => h.object.userData && h.object.userData.type);
      if (hits.length) { const o = hits[0].object; focusBody(o); showBodyInfo(o.userData.type, o.userData.data); }
    }
  });

  renderer.domElement.addEventListener('pointermove', e => {
    if (flying || mode !== 'universe') { tooltip.style.display = 'none'; return; }
    const id = nearestSystemToCursor(e.clientX, e.clientY);
    if (id == null) { tooltip.style.display = 'none'; return; }
    const s = sysById[id];
    tooltip.style.display = 'block';
    tooltip.style.left = (e.clientX + 14) + 'px';
    tooltip.style.top = (e.clientY + 14) + 'px';
    tooltip.innerHTML = 'System #' + id + '<br>metallicity ' + s.metallicity.toFixed(2) + '<br>planets ' + (planetCount[id] || 0);
  });

  function focusBody(o) {
    const p = o.position.clone(); const r = o.userData.radius || 1;
    const dir = new THREE.Vector3().subVectors(camera.position, p).normalize();
    startFlight(p.clone().add(dir.multiplyScalar(Math.max(8, r * 8 + 6))), p);
  }

  // ---- info panels ----
  function row(k, v) { return '<tr><td class="k">' + k + '</td><td>' + v + '</td></tr>'; }
  function showSystemInfo(s) {
    const ns = (starsBySys[s.id] || []).length, np = planetCount[s.id] || 0;
    document.getElementById('info').innerHTML = '<h3>System #' + s.id + '</h3><table>' +
      row('metallicity', s.metallicity.toFixed(3)) + row('density', s.density.toFixed(3)) +
      row('H', s.H.toFixed(3)) + row('He', s.He.toFixed(3)) + row('C', s.C.toFixed(3)) + row('O', s.O.toFixed(3)) +
      row('stars', ns) + row('planets', np) +
      '</table><div style="margin-top:6px;color:#7f9bc4">Click a star or planet.</div>';
  }
  function showBodyInfo(type, d) {
    let h = '<h3>' + (type === 'star' ? 'Star #' + d.id : (type === 'planet' ? 'Planet (order ' + d.orbital_order + ')' : 'Moon #' + d.id)) + '</h3><table>';
    if (type === 'star') {
      h += row('system', d.system_id) + row('star #', d.star_number) + row('spectral', d.spectral_type) +
        row('mass', d.mass.toFixed(3) + ' M&#9737;') + row('radius', d.radius.toFixed(3) + ' R&#9737;') +
        row('temp', d.temperature.toFixed(0) + ' K') + row('luminosity', d.luminosity.toFixed(3) + ' L&#9737;') +
        row('metallicity', d.metallicity.toFixed(3));
    } else if (type === 'planet') {
      h += row('system', d.system_id) + row('star', d.star_id) + row('order', d.orbital_order) +
        row('type', d.planet_type) + row('mass', d.mass.toFixed(2) + ' M&#8853;') +
        row('radius', d.radius.toFixed(2) + ' R&#8853;') + row('temp', d.temperature.toFixed(0) + ' K') +
        row('albedo', d.albedo.toFixed(2)) + row('orbit', d.orbital_distance.toFixed(3) + ' AU');
    } else {
      h += row('planet', d.planet_id) + row('order', d.orbital_order) +
        row('mass', d.mass.toFixed(3)) + row('radius', d.radius.toFixed(3)) +
        row('orbit', d.orbital_distance.toFixed(4) + ' AU');
    }
    h += '</table>';
    document.getElementById('info').innerHTML = h;
  }

  // ---- search / filter ----
  const SPECS = ['O', 'B', 'A', 'F', 'G', 'K', 'M'];
  (function () {
    const box = document.getElementById('specBoxes');
    SPECS.forEach(sp => {
      const l = document.createElement('label');
      const cb = document.createElement('input'); cb.type = 'checkbox'; cb.value = sp; cb.checked = true;
      l.appendChild(cb); l.appendChild(document.createTextNode(sp)); box.appendChild(l);
    });
  })();
  function applyFilter() {
    const metMin = +document.getElementById('metMin').value;
    const metMax = +document.getElementById('metMax').value;
    const minP = +document.getElementById('minP').value;
    const specs = Array.from(document.querySelectorAll('#specBoxes input:checked')).map(c => c.value);
    const visible = systems.filter(s => {
      if (s.metallicity < metMin || s.metallicity > metMax) return false;
      if ((planetCount[s.id] || 0) < minP) return false;
      if (specs.length < SPECS.length) {
        const sp = (starsBySys[s.id] || []).map(st => st.spectral_type);
        if (!sp.some(x => specs.includes(x))) return false;
      }
      return true;
    });
    buildSystems(visible);
    document.getElementById('matchCount').textContent = visible.length + ' shown';
    const ml = document.getElementById('matchList'); ml.innerHTML = '';
    visible.slice(0, 200).forEach(s => {
      const d = document.createElement('div');
      d.textContent = '#' + s.id + ' (met ' + s.metallicity.toFixed(2) + ', planets ' + (planetCount[s.id] || 0) + ')';
      d.onclick = () => enterSystem(s.id); ml.appendChild(d);
    });
  }
  document.getElementById('applyF').onclick = applyFilter;
  document.getElementById('backBtn').onclick = exitSystem;
  document.getElementById('goId').onclick = () => {
    const v = parseInt(document.getElementById('sysId').value, 10);
    if (sysById[v]) enterSystem(v);
  };
  addEventListener('keydown', e => { if (e.key === 'Escape') exitSystem(); });

  // ---- init ----
  buildSystems(systems);
  applyFilter();

  // ---- render loop ----
  function animate() {
    requestAnimationFrame(animate);
    if (flying) {
      controls.target.lerp(desiredTarget, 0.1);
      camera.position.lerp(desiredCam, 0.1);
      camera.lookAt(controls.target);
      if (camera.position.distanceTo(desiredCam) < 1.5 && controls.target.distanceTo(desiredTarget) < 1.5) {
        flying = false;
        controls.enabled = true;
      }
    } else {
      // free-fly: translate camera and target together so look direction is kept
      const dt = Math.min(clock.getDelta(), 0.05);
      const fwd = new THREE.Vector3(); camera.getWorldDirection(fwd);
      const right = new THREE.Vector3().crossVectors(fwd, UP).normalize();
      const move = new THREE.Vector3();
      if (keys.KeyW) move.add(fwd);
      if (keys.KeyS) move.sub(fwd);
      if (keys.KeyD) move.add(right);
      if (keys.KeyA) move.sub(right);
      if (keys.Space) move.add(UP);
      if (keys.ControlLeft || keys.ControlRight) move.sub(UP);
      if (move.lengthSq() > 0) {
        const sp = (keys.ShiftLeft || keys.ShiftRight ? FLY_FAST : FLY_SLOW) * dt;
        move.normalize().multiplyScalar(sp);
        camera.position.add(move);
        controls.target.add(move);
      }
      controls.update();
    }
    renderer.render(scene, camera);
  }
  animate();
  addEventListener('resize', () => {
    camera.aspect = innerWidth / innerHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(innerWidth, innerHeight);
  });
})();
</script>
</body>
</html>
"""


def main():
    if not os.path.exists(DB_PATH):
        raise SystemExit(f"{DB_PATH} not found. Run universe.py first to generate it.")
    if not os.path.exists(os.path.join(SCRIPT_DIR, "viewer", "three.min.js")):
        raise SystemExit("viewer/three.min.js missing. Re-run the three.js vendoring step.")

    data = collect(DB_PATH)
    html = HTML_TEMPLATE.replace("___DATA___", json.dumps(data))
    with open(OUT_PATH, "w") as f:
        f.write(html)

    print(
        f"Wrote {OUT_PATH}: {len(data['systems'])} systems, "
        f"{len(data['stars'])} stars, {len(data['planets'])} planets, "
        f"{len(data['moons'])} moons"
    )


if __name__ == "__main__":
    main()
