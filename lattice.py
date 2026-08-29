#!/usr/bin/env python3

import numpy as np
from noise import pnoise3

from config import Config

conf = Config()

# =========================
# LATTICE
# =========================

def perlin(x, y, z, seed):
    return (
        pnoise3(
            x,
            y,
            z,
            base=seed,
            octaves=conf.element_octaves
        ) + 1
    ) / 2


def generate_lattice():
    lattice = np.zeros(
        (
            conf.lattice_resolution,
            conf.lattice_resolution,
            conf.lattice_resolution
        ),
        dtype=[
            ("density", "f4"),
            ("C", "f4"),
            ("O", "f4"),
            ("He", "f4"),
            ("H", "f4"),
            ("metallicity", "f4"),
        ]
    )

    # =========================
    # GENERATE LATTICE
    # =========================

    for z in range(len(conf.lattice_steps)):
        for y in range(len(conf.lattice_steps)):
            for x in range(len(conf.lattice_steps)):

                density = perlin(
                    conf.lattice_steps[x],
                    conf.lattice_steps[y],
                    conf.lattice_steps[z],
                    conf.density_seed
                )

                lattice[x, y, z]["density"] = density

                lattice[x, y, z]["C"] = (
                    perlin(
                        conf.lattice_steps[x],
                        conf.lattice_steps[y],
                        conf.lattice_steps[z],
                        conf.carbon_seed
                    ) * density
                )

                lattice[x, y, z]["O"] = (
                    perlin(
                        conf.lattice_steps[x],
                        conf.lattice_steps[y],
                        conf.lattice_steps[z],
                        conf.oxygen_seed
                    ) * density
                )

                lattice[x, y, z]["He"] = (
                    perlin(
                        conf.lattice_steps[x],
                        conf.lattice_steps[y],
                        conf.lattice_steps[z],
                        conf.helium_seed
                    ) * density
                )

                lattice[x, y, z]["H"] = (
                    perlin(
                        conf.lattice_steps[x],
                        conf.lattice_steps[y],
                        conf.lattice_steps[z],
                        conf.hydrogen_seed
                    ) * density
                )

                lattice[x, y, z]["metallicity"] = perlin(
                    conf.lattice_steps[x],
                    conf.lattice_steps[y],
                    conf.lattice_steps[z],
                    conf.metallicity_seed
                )
    return lattice
