#!/usr/bin/env python3

import numpy as np

# reference data

REFERENCE_MASSES = np.array([
    0.40,
    0.80,
    1.10,
    1.70,
    3.30,
    16.0,
    40.0,
])

REFERENCE_RADII = np.array([
    0.60,
    0.80,
    1.10,
    1.40,
    2.50,
    7.00,
    18.0,
])

# kroupa initial mass function
def _power_law_integral(minimum, maximum, alpha):
    if alpha == 1:
        return np.log(maximum / minimum)
    return (maximum ** (1 - alpha) - minimum ** (1 - alpha)) / (1 - alpha)

def _sample_power_law(rng, minimum, maximum, alpha):
    u = rng.random()
    exponent = 1 - alpha
    return (
        minimum ** exponent
        + u * (maximum ** exponent - minimum ** exponent)
    ) ** (1 / exponent)

def generate_mass(rng):
    low_min = 0.179
    low_max = 0.50
    low_alpha = 1.3
    high_min = 0.50
    high_max = 31.0
    high_alpha = 2.3
    low_coefficient = 1.0
    high_coefficient = 0.5 ** (high_alpha - low_alpha)
    low_weight = low_coefficient * _power_law_integral(
        low_min, low_max, low_alpha
    )
    high_weight = high_coefficient * _power_law_integral(
        high_min, high_max, high_alpha
    )
    low_probability = low_weight / (low_weight + high_weight)
    if rng.random() < low_probability:
        return _sample_power_law(rng, low_min, low_max, low_alpha)
    return _sample_power_law(rng, high_min, high_max, high_alpha)

# mass to luminosity
def generate_luminosity(mass):
    log_mass = np.log10(mass)
    if mass <= 0.45:
        log_luminosity = 2.028 * log_mass - 0.976
    elif mass <= 0.72:
        log_luminosity = 4.572 * log_mass - 0.102
    elif mass <= 1.05:
        log_luminosity = 5.743 * log_mass - 0.007
    elif mass <= 2.40:
        log_luminosity = 4.329 * log_mass + 0.010
    elif mass <= 7.0:
        log_luminosity = 3.967 * log_mass + 0.093
    else:
        log_luminosity = 2.865 * log_mass + 1.105
    return 10 ** log_luminosity

# mass to radius
def generate_radius(mass, luminosity):
    if mass <= 1.5:
        return (
            0.438 * mass ** 2
            + 0.479 * mass
            + 0.075
        )
    temperature = generate_temperature(mass)
    return np.sqrt(
        luminosity / (temperature / 5772.0) ** 4
    )

# mass to temperature
def generate_temperature(mass, luminosity=None, radius=None):
    if mass > 1.5:
        log_mass = np.log10(mass)
        log_temperature = (
            -0.170 * log_mass ** 2
            + 0.888 * log_mass
            + 3.671
        )
        return 10 ** log_temperature
    if luminosity is None or radius is None:
        raise ValueError(
            "luminosity and radius are required for masses <= 1.5"
        )
    return 5772.0 * (
        luminosity / radius ** 2
    ) ** 0.25

# temperature to spectral class
def generate_spectral_type(temperature):
    if temperature >= 30000:
        return "O"
    if temperature >= 10000:
        return "B"
    if temperature >= 7500:
        return "A"
    if temperature >= 6000:
        return "F"
    if temperature >= 5200:
        return "G"
    if temperature >= 3700:
        return "K"
    return "M"

# star
def generate_star(rng, system, system_index):
    mass = generate_mass(rng)
    luminosity = generate_luminosity(mass)
    if mass <= 1.5:
        radius = generate_radius(mass, luminosity)
        temperature = generate_temperature(
            mass,
            luminosity,
            radius,
        )
    else:
        temperature = generate_temperature(mass)
        radius = generate_radius(mass, luminosity)
    spectral_type = generate_spectral_type(temperature)
    return {
        "system_index": system_index,
        "mass": mass,
        "radius": radius,
        "luminosity": luminosity,
        "temperature": temperature,
        "spectral_type": spectral_type,
        "metallicity": float(system["metallicity"]),
    }

def generate_stars(rng, systems):
    stars = []
    for system_index, system in enumerate(systems):
        number_of_stars = rng.integers(1, 4)
        for star_number in range(number_of_stars):
            star = generate_star(rng, system, system_index)
            star["star_number"] = star_number
            stars.append(star)
    return stars
