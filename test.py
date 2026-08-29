#!/usr/bin/env python3

from noise import pnoise3
import plotly.graph_objects as go

SIZE = 10
RESOLUTION = 40
SCALE = 0.1

OXYGEN_THRESHOLD = 0.5
IRON_THRESHOLD = 0.5

x_values = []
y_values = []
z_values = []

for x in range(RESOLUTION):
    for y in range(RESOLUTION):
        for z in range(RESOLUTION):

            nx = x / RESOLUTION * SIZE * SCALE
            ny = y / RESOLUTION * SIZE * SCALE
            nz = z / RESOLUTION * SIZE * SCALE

            oxygen = (pnoise3(nx, ny, nz, base=123) + 1) / 2
            iron = (pnoise3(nx, ny, nz, base=456) + 1) / 2

            # Only plot the overlap
            if oxygen >= OXYGEN_THRESHOLD and iron >= IRON_THRESHOLD:
                x_values.append(x / RESOLUTION * SIZE)
                y_values.append(y / RESOLUTION * SIZE)
                z_values.append(z / RESOLUTION * SIZE)


fig = go.Figure(
    data=go.Scatter3d(
        x=x_values,
        y=y_values,
        z=z_values,
        mode="markers",
        marker=dict(size=3, opacity=0.5),
    )
)

fig.update_layout(
    title="Oxygen ≥ 0.3 AND Iron ≥ 0.4",
    scene=dict(
        xaxis_title="X",
        yaxis_title="Y",
        zaxis_title="Z",
    ),
)

fig.show()
