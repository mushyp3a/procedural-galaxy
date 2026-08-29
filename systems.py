#!/usr/bin/env python3

import numpy as np
from config import Config

conf = Config()

# =========================
# GENERATE SYSTEMS
# =========================

def generate_systems(lattice, rng):
    systems = []

    cell_size = conf.universe_size / conf.lattice_resolution

    system_mask = (
        (lattice["density"] > 0.5)
        & (lattice["H"] > 0.3)
        & (lattice["He"] > 0.3)
    )

    candidate_coordinates = np.argwhere(system_mask)

    rng.shuffle(candidate_coordinates)

    for x, y, z in candidate_coordinates:

        density = lattice[x, y, z]["density"]
        hydrogen = lattice[x, y, z]["H"]
        helium = lattice[x, y, z]["He"]

        probability = density * hydrogen * helium

        if rng.random() > probability:
            continue

        max_offset = cell_size * 0.4

        offset = rng.uniform(
            -max_offset,
            max_offset,
            3
        )

        position = (
            np.array([x, y, z]) * cell_size
            + offset
        )

        systems.append({
            "x": position[0],
            "y": position[1],
            "z": position[2],

            "density": float(density),
            "H": float(hydrogen),
            "He": float(helium),
            "C": float(lattice[x, y, z]["C"]),
            "O": float(lattice[x, y, z]["O"]),
            "metallicity": float(lattice[x, y, z]["metallicity"]),
        })


    print(f"Generated {len(systems)} systems")
    return systems
