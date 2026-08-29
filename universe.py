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

conf = Config()

rng = np.random.default_rng(conf.seed)

db = Database("universe.db")
db.initialise()

lattice = generate_lattice()
systems = generate_systems(lattice, rng)

db.save_systems(systems)
db.close()

plot_suitability(lattice)
plot_systems(systems)
