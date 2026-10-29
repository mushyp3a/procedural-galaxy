#!/usr/bin/env python3

import math
import numpy as np

# planet generation

MIN_ORBITAL_DISTANCE = 0.05
MAX_ORBITAL_DISTANCE = 30.0

MIN_PLANET_MASS = 0.1
MAX_PLANET_MASS = 4000.0

# planet count

def generate_planet_count(star, rng):
    # how many planets a star gets, bigger stars get fewer
    # not real physics just based on what we see

    mass = star["mass"]
    metallicity = star["metallicity"]

    if mass < 0.6:
        expected = 5.0
    elif mass < 1.0:
        expected = 4.0
    elif mass < 1.5:
        expected = 3.5
    else:
        expected = 3.0

    metallicity_factor = 0.75 + 0.5 * metallicity
    expected *= metallicity_factor

    count = rng.poisson(expected)

    return max(1, min(int(count), 10))

# snow line

def generate_snow_line(star):
    # snow line distance in AU, further out for brighter stars

    luminosity = star["luminosity"]

    return 2.7 * math.sqrt(luminosity)

# orbital distances

def generate_orbital_distances(planet_count, star, rng):
    # distances in AU, each orbit is further out than the last

    if planet_count == 1:
        return np.array([
            rng.uniform(
                MIN_ORBITAL_DISTANCE,
                MAX_ORBITAL_DISTANCE,
            )
        ])

    first_distance = rng.uniform(
        MIN_ORBITAL_DISTANCE,
        min(0.5, MAX_ORBITAL_DISTANCE),
    )

    ratio = rng.uniform(1.5, 2.5)

    distances = [first_distance]

    for _ in range(planet_count - 1):
        next_distance = distances[-1] * ratio

        if next_distance > MAX_ORBITAL_DISTANCE:
            break

        distances.append(next_distance)

    return np.array(distances)

# planet mass

def generate_planet_mass(star, orbital_distance, rng):
    # mass in earth masses
    # inner planets are small and rocky, outer ones can get much bigger
    # higher metallicity makes them a bit heavier

    metallicity = star["metallicity"]
    snow_line = generate_snow_line(star)

    metal_factor = 0.6 + 0.8 * metallicity

    if orbital_distance < snow_line:
        minimum = 0.1
        maximum = 10.0
    else:
        minimum = 1.0
        maximum = 4000.0

    mass = 10 ** rng.uniform(
        math.log10(minimum),
        math.log10(maximum),
    )

    mass *= metal_factor

    return float(
        np.clip(
            mass,
            MIN_PLANET_MASS,
            MAX_PLANET_MASS,
        )
    )

# planet type

def generate_planet_type(mass, orbital_distance, star):
    # works out the type from the mass and if its past the snow line

    snow_line = generate_snow_line(star)

    if mass < 10:
        return "terrestrial"

    if orbital_distance >= snow_line and mass < 100:
        return "ice_giant"

    return "gas_giant"

# mass to radius

def generate_radius(mass):
    # radius in earth radii, uses the chen and kipping mass radius relation

    if mass < 2.04:
        coefficient = 1.008
        exponent = 0.279

    elif mass < 132:
        coefficient = 1.008
        exponent = 0.589

    else:
        coefficient = 11.0
        exponent = -0.044

    return float(
        coefficient * mass ** exponent
    )

# albedo

def generate_albedo(planet_type, rng):
    # random albedo kept between limits, we dont model atmospheres so cant work it out

    if planet_type == "terrestrial":
        minimum = 0.1
        maximum = 0.6

    elif planet_type == "ice_giant":
        minimum = 0.2
        maximum = 0.7

    else:
        minimum = 0.2
        maximum = 0.6

    return float(
        rng.uniform(
            minimum,
            maximum,
        )
    )

# equilibrium temperature

def generate_temperature(
    luminosity,
    orbital_distance,
    albedo,
):
    # temperature in kelvin
    # assumes heat is spread evenly and no greenhouse effect

    solar_equilibrium_temperature = 278.5

    return float(
        solar_equilibrium_temperature
        * luminosity ** 0.25
        * (1 - albedo) ** 0.25
        * orbital_distance ** -0.5
    )

# single planet

def generate_planet(
    star,
    orbital_order,
    orbital_distance,
    rng,
):
    # makes one planet

    mass = generate_planet_mass(
        star,
        orbital_distance,
        rng,
    )

    planet_type = generate_planet_type(
        mass,
        orbital_distance,
        star,
    )

    radius = generate_radius(
        mass,
    )

    albedo = generate_albedo(
        planet_type,
        rng,
    )

    temperature = generate_temperature(
        star["luminosity"],
        orbital_distance,
        albedo,
    )

    return {
        "star_index": star.get("star_index"),
        "system_index": star.get("system_index"),
        "orbital_order": orbital_order,
        "orbital_distance": float(orbital_distance),
        "mass": mass,
        "radius": radius,
        "planet_type": planet_type,
        "albedo": albedo,
        "temperature": temperature,
    }

# planets around one star

def generate_planets(star, rng):
    # makes all the planets for one star

    planet_count = generate_planet_count(
        star,
        rng,
    )

    orbital_distances = generate_orbital_distances(
        planet_count,
        star,
        rng,
    )

    planets = []

    for orbital_order, orbital_distance in enumerate(
        orbital_distances,
        start=1,
    ):
        planets.append(
            generate_planet(
                star,
                orbital_order,
                orbital_distance,
                rng,
            )
        )

    return planets

# all stars

def generate_all_planets(stars, rng):
    # makes planets for every star, gives back a list of dicts

    planets = []

    for star_index, star in enumerate(stars):
        star = dict(star)
        star["star_index"] = star_index

        planets.extend(
            generate_planets(
                star,
                rng,
            )
        )

    return planets
