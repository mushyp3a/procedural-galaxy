#!/usr/bin/env python3

from dataclasses import dataclass, field
import numpy as np


@dataclass
class Config:
    seed: int = 125

    carbon_seed: int = field(init=False)
    oxygen_seed: int = field(init=False)
    helium_seed: int = field(init=False)
    hydrogen_seed: int = field(init=False)
    metallicity_seed: int = field(init=False)
    density_seed: int = field(init=False)

    universe_size: float = 1000
    element_noise_scale: float = 0.005
    element_octaves: int = 1

    lattice_resolution: int = 50
    lattice_steps: np.ndarray = field(init=False)

    def __post_init__(self):
        self.lattice_steps = np.round(
            np.linspace(
                0,
                self.universe_size * self.element_noise_scale,
                self.lattice_resolution
            ),
            2
        )
        self.carbon_seed = self.seed + 1
        self.oxygen_seed = self.seed + 2
        self.helium_seed = self.seed + 3
        self.hydrogen_seed = self.seed + 4
        self.metallicity_seed = self.seed + 5
        self.density_seed = self.seed + 6
