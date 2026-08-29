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

    systems_fig = go.Figure(
        data=go.Scatter3d(
            x=system_coordinates[:, 0],
            y=system_coordinates[:, 1],
            z=system_coordinates[:, 2],
            mode="markers",
            marker=dict(
                size=3,
                opacity=0.7,
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

def plot_density(lattice):
    density_mask = lattice["density"] > 0.6
    density_coordinates = np.argwhere(density_mask)

    density_fig = go.Figure(
        data=go.Scatter3d(
            x=density_coordinates[:, 0],
            y=density_coordinates[:, 1],
            z=density_coordinates[:, 2],
            mode="markers",
            marker=dict(
                size=3,
                opacity=0.5,
            ),
        )
    )

    density_fig.update_layout(
        scene=dict(
            xaxis_title="X",
            yaxis_title="Y",
            zaxis_title="Z",
            aspectmode="cube",
        ),
        title="Points where Density > 0.6",
    )

    density_fig.show()

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

def plot_iron(lattice):
    iron_mask = lattice["Fe"] > 0.6
    iron_coordinates = np.argwhere(iron_mask)

    iron_fig = go.Figure(
        data=go.Scatter3d(
            x=iron_coordinates[:, 0],
            y=iron_coordinates[:, 1],
            z=iron_coordinates[:, 2],
            mode="markers",
            marker=dict(
                size=3,
                opacity=0.5,
            ),
        )
    )

    iron_fig.update_layout(
        scene=dict(
            xaxis_title="X",
            yaxis_title="Y",
            zaxis_title="Z",
            aspectmode="cube",
        ),
        title="Points where Fe > 0.6",
    )

    iron_fig.show()
