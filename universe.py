#!/usr/bin/env python3

# import sqlite3
# from noise import pnoise3
# import plotly.graph_objects as go
import numpy as np

from config import Config
from lattice import generate_lattice
from systems import generate_systems
from database import Database
from visualise import plot_systems, plot_suitability, plot_iron, plot_density
from stars import generate_stars
from planets import generate_planets

conf = Config()

rng = np.random.default_rng(conf.seed)

db = Database("universe.db")
db.initialise()

lattice = generate_lattice()
systems = generate_systems(lattice, rng)
stars = generate_stars(rng, systems)
planets = generate_planets(stars, rng)

system_ids = db.save_systems(systems)
db.save_stars(stars, system_ids)
db.save_planets(planets, system_ids)

db.close()
plot_suitability(lattice)
plot_systems(systems)
