#!/usr/bin/env python3

import plotly.graph_objects as go
import numpy as np
from config import Config

conf = Config()

# =========================
# GENERATE SYSTEMS
# =========================

def plot_systems(systems):
    system_coordinates = np.array([
        [system["x"], system["y"], system["z"]]
        for system in systems
    ])

    metallicities = np.array([system["metallicity"] for system in systems])
    densities = np.array([system["density"] for system in systems])

    systems_fig = go.Figure(
        data=go.Scatter3d(
            x=system_coordinates[:, 0],
            y=system_coordinates[:, 1],
            z=system_coordinates[:, 2],
            mode="markers",
            marker=dict(
                size=2 + 6 * densities,
                color=metallicities,
                colorscale="Viridis",
                opacity=0.7,
                colorbar=dict(title="Metallicity"),
            ),
        )
    )

    systems_fig.update_layout(
        scene=dict(
            xaxis_title="X",
            yaxis_title="Y",
            zaxis_title="Z",
            aspectmode="cube",
            xaxis=dict(range=[0, conf.universe_size]),
            yaxis=dict(range=[0, conf.universe_size]),
            zaxis=dict(range=[0, conf.universe_size]),
        ),
        title=f"Created Systems ({len(systems)})",
    )

    systems_fig.show()

def plot_suitability(lattice):
    mask = (
        (lattice["He"] > 0.3)
        & (lattice["H"] > 0.3)
        & (lattice["density"] > 0.6)
    )

    coordinates = np.argwhere(mask)

    gas_fig = go.Figure(
        data=go.Scatter3d(
            x=coordinates[:, 0],
            y=coordinates[:, 1],
            z=coordinates[:, 2],
            mode="markers",
            marker=dict(
                size=3,
                opacity=0.5,
            ),
        )
    )

    gas_fig.update_layout(
        scene=dict(
            xaxis_title="X",
            yaxis_title="Y",
            zaxis_title="Z",
            aspectmode="cube",
        ),
        title="Points where H > 0.3 and He > 0.3",
    )

    gas_fig.show()

def plot_metallicity(lattice):
    metallicity_mask = lattice["metallicity"] > 0.6
    metallicity_coordinates = np.argwhere(metallicity_mask)

    metallicity_fig = go.Figure(
        data=go.Scatter3d(
            x=metallicity_coordinates[:, 0],
            y=metallicity_coordinates[:, 1],
            z=metallicity_coordinates[:, 2],
            mode="markers",
            marker=dict(
                size=3,
                opacity=0.5,
            ),
        )
    )

    metallicity_fig.update_layout(
        scene=dict(
            xaxis_title="X",
            yaxis_title="Y",
            zaxis_title="Z",
            aspectmode="cube",
        ),
        title="Points where Metallicity > 0.6",
    )

    metallicity_fig.show()


# =========================
# DETAILLED SYSTEM VIEW
# =========================

SPECTRAL_COLORS = {
    "O": "#9bb0ff",
    "B": "#aabfff",
    "A": "#cad7ff",
    "F": "#f8f7ff",
    "G": "#fff4e8",
    "K": "#ffd2a1",
    "M": "#ffcc6f",
}

PLANET_COLORS = {
    "terrestrial": "#4caf50",
    "ice_giant": "#64b5f6",
    "gas_giant": "#ff7043",
}


def _orbit_points(center, a, incl, n=64):
    """Return (x, y, z) arrays tracing a circular orbit of radius a,
    inclined by `incl` about the x-axis, centred on `center`."""
    theta = np.linspace(0, 2 * np.pi, n)
    x = a * np.cos(theta)
    y = a * np.sin(theta) * np.cos(incl)
    z = a * np.sin(theta) * np.sin(incl)
    return center[0] + x, center[1] + y, center[2] + z


def _body_position(center, a, incl, phase):
    x = a * np.cos(phase)
    y = a * np.sin(phase) * np.cos(incl)
    z = a * np.sin(phase) * np.sin(incl)
    return center + np.array([x, y, z])


def plot_system(conn, system_id, output_html="system_detail.html", show=True):
    # Read the system and its bodies from the database.
    system = conn.execute(
        """
        SELECT id, x, y, z, metallicity, density
        FROM systems WHERE id = ?
        """,
        (system_id,),
    ).fetchone()

    if system is None:
        raise ValueError(f"system {system_id} not found")

    sys_id, sx, sy, sz, met, dens = system

    stars = conn.execute(
        """
        SELECT id, star_number, mass, radius, temperature,
               luminosity, spectral_type
        FROM stars WHERE system_id = ?
        """,
        (sys_id,),
    ).fetchall()

    planets = conn.execute(
        """
        SELECT id, star_id, orbital_order, orbital_distance,
               mass, radius, temperature, planet_type
        FROM planets WHERE system_id = ?
        """,
        (sys_id,),
    ).fetchall()

    moons = conn.execute(
        """
        SELECT id, planet_id, orbital_order, orbital_distance, mass, radius
        FROM moons
        WHERE planet_id IN (SELECT id FROM planets WHERE system_id = ?)
        """,
        (sys_id,),
    ).fetchall()

    # Deterministic geometry so a given system always renders the same.
    rng = np.random.default_rng(sys_id)

    fig = go.Figure()

    # --- Stars (separated slightly if multiple) ---
    star_positions = {}
    n_stars = len(stars)
    for i, st in enumerate(stars):
        angle = 2 * np.pi * i / n_stars if n_stars > 1 else 0
        sep = 0.5 if n_stars > 1 else 0.0
        pos = np.array([sep * np.cos(angle), sep * np.sin(angle), 0.0])
        star_positions[st[0]] = pos
        fig.add_trace(go.Scatter3d(
            x=[pos[0]], y=[pos[1]], z=[pos[2]],
            mode="markers",
            marker=dict(size=8, color=SPECTRAL_COLORS.get(st[6], "#ffffff")),
            name=f"Star {st[1]} ({st[6]})",
        ))

    # --- Planets on orbits ---
    planet_positions = {}
    for pl in planets:
        pid, star_id, order, a, pmass, prad, ptemp, ptype = pl
        center = star_positions.get(star_id, np.zeros(3))
        phase = rng.uniform(0, 2 * np.pi)
        incl = rng.uniform(0, np.pi)

        ox, oy, oz = _orbit_points(center, a, incl)
        fig.add_trace(go.Scatter3d(
            x=ox, y=oy, z=oz, mode="lines",
            line=dict(width=1, color="rgba(150,150,150,0.35)"),
            showlegend=False, hoverinfo="skip",
        ))

        pos = _body_position(center, a, incl, phase)
        planet_positions[pid] = pos
        fig.add_trace(go.Scatter3d(
            x=[pos[0]], y=[pos[1]], z=[pos[2]],
            mode="markers",
            marker=dict(size=5, color=PLANET_COLORS.get(ptype, "#ffffff")),
            name=f"P{order} {ptype} ({a:.2f} AU)",
        ))

    # --- Moons on planet orbits ---
    for mn in moons:
        mid, planet_id, order, ma, mmass, mrad = mn
        if planet_id not in planet_positions:
            continue
        center = planet_positions[planet_id]
        phase = rng.uniform(0, 2 * np.pi)
        incl = rng.uniform(0, np.pi)

        ox, oy, oz = _orbit_points(center, ma, incl, n=32)
        fig.add_trace(go.Scatter3d(
            x=ox, y=oy, z=oz, mode="lines",
            line=dict(width=1, color="rgba(200,200,200,0.25)"),
            showlegend=False, hoverinfo="skip",
        ))

        pos = _body_position(center, ma, incl, phase)
        fig.add_trace(go.Scatter3d(
            x=[pos[0]], y=[pos[1]], z=[pos[2]],
            mode="markers",
            marker=dict(size=2, color="#cccccc"),
            name=f"moon {order} ({ma:.3f} AU)",
        ))

    fig.update_layout(
        title=(
            f"System {sys_id} &mdash; metallicity={met:.2f}, "
            f"density={dens:.2f}, {n_stars} star(s), "
            f"{len(planets)} planet(s), {len(moons)} moon(s)"
        ),
        scene=dict(aspectmode="data"),
    )

    fig.write_html(output_html)
    if show:
        fig.show()
    return output_html
