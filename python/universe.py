#!/usr/bin/env python3

# import sqlite3
# from noise import pnoise3
# import plotly.graph_objects as go
import numpy as np

from config import Config
from lattice import generate_lattice
from systems import generate_systems
from database import Database
from visualise import (
    plot_systems,
    plot_suitability,
    plot_metallicity,
    plot_system,
)
from stars import generate_stars
from planets import generate_all_planets

conf = Config()

rng = np.random.default_rng(conf.seed)

db = Database("universe.db")
db.initialise()

lattice = generate_lattice()
systems = generate_systems(lattice, rng)
stars = generate_stars(rng, systems)
planets = generate_all_planets(stars, rng)

system_ids = db.save_systems(systems)
star_ids = db.save_stars(stars, system_ids)
db.save_planets(planets, system_ids, star_ids)

# Detailed view of the system with the most planets (writes an HTML file).
richest = db.connection.execute(
    "SELECT system_id FROM planets "
    "GROUP BY system_id ORDER BY COUNT(*) DESC LIMIT 1"
).fetchone()
if richest:
    plot_system(
        db.connection,
        richest[0],
        output_html="system_detail.html",
        show=False,
    )

db.close()
plot_suitability(lattice)
plot_systems(systems)
