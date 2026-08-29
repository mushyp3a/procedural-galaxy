#!/usr/bin/env python3

import math
import numpy as np

# =========================
# PLANET GENERATION
# =========================

MIN_ORBITAL_DISTANCE = 0.05
MAX_ORBITAL_DISTANCE = 30.0

MIN_PLANET_MASS = 0.1
MAX_PLANET_MASS = 4000.0

# =========================
# PLANET COUNT
# =========================

def generate_planet_count(star, rng):
    # Generate the number of planets around a star.
    # This is a probabilistic procedural model informed by observed
    # differences in planet occurrence with stellar properties.
    # It is not an exact planet-formation equation.

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

# =========================
# SNOW LINE
# =========================

def generate_snow_line(star):
    # estimate the snow-line distance in AU.
    # The location is scaled with stellar luminosity because the
    # stellar radiation field determines the distance at which
    # volatile compounds can condense.

    luminosity = star["luminosity"]

    return 2.7 * math.sqrt(luminosity)

# =========================
# ORBITAL DISTANCES
# =========================

def generate_orbital_distances(planet_count, star, rng):
    # Generate ordered planetary orbital distances in AU.
    # Orbits are generated geometrically rather than independently,
    # producing increasing orbital spacing.

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

# =========================
# PLANET MASS
# =========================

def generate_planet_mass(star, orbital_distance, rng):
    # Generate planet mass in Earth masses.
    # Inner regions favour smaller rocky planets while the outer
    # region allows substantially larger planets.
    # Metallicity acts as a procedural modifier for the amount of
    # heavy-element material available.
    # This is a procedural formation model, not a physical
    # simulation of planetary accretion.

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

# =========================
# PLANET TYPE
# =========================

def generate_planet_type(mass, orbital_distance, star):
    # Classify a planet using mass and its position relative
    # to the stellar snow line.

    snow_line = generate_snow_line(star)

    if mass < 10:
        return "terrestrial"

    if orbital_distance >= snow_line and mass < 100:
        return "ice_giant"

    return "gas_giant"

# =========================
# MASS -> RADIUS
# =========================

def generate_radius(mass):
    # Estimate radius in Earth radii using the Chen & Kipping
    # probabilistic mass-radius relation.
    # The relation is represented as piecewise power laws.

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

# =========================
# ALBEDO
# =========================

def generate_albedo(planet_type, rng):
    # Generate a bounded procedural Bond-albedo estimate.
    # Atmospheric and surface composition are not sufficiently
    # modelled to calculate albedo directly.

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

# =========================
# EQUILIBRIUM TEMPERATURE
# =========================

def generate_temperature(
    luminosity,
    orbital_distance,
    albedo,
):
    # Calculate planetary equilibrium temperature in Kelvin.
    # Assumes:
    # - radiative equilibrium
    # - uniform heat redistribution
    # - no greenhouse effect

    solar_equilibrium_temperature = 278.5

    return float(
        solar_equilibrium_temperature
        * luminosity ** 0.25
        * (1 - albedo) ** 0.25
        * orbital_distance ** -0.5
    )

# =========================
# HABITABILITY
# =========================

def generate_habitability(
    planet_type,
    temperature,
    orbital_distance,
    star,
):
    # Generate a continuous 0-1 environmental suitability score.
    # This is NOT a probability of life.
    # It represents how suitable the basic physical environment
    # is for Earth-like surface conditions.

    luminosity = star["luminosity"]

    # Simple luminosity-based conservative HZ approximation.
    inner_hz = math.sqrt(
        luminosity / 1.1
    )

    outer_hz = math.sqrt(
        luminosity / 0.35
    )

    if inner_hz <= orbital_distance <= outer_hz:
        zone_score = 1.0
    else:
        if orbital_distance < inner_hz:
            distance = inner_hz - orbital_distance
        else:
            distance = orbital_distance - outer_hz

        zone_width = outer_hz - inner_hz

        zone_score = max(
            0.0,
            1.0 - distance / zone_width,
        )

    # Temperature suitability.
    temperature_score = math.exp(
        -(
            (temperature - 288.0) / 70.0
        ) ** 2
    )

    if planet_type == "terrestrial":
        type_score = 1.0
    elif planet_type == "ice_giant":
        type_score = 0.15
    else:
        type_score = 0.05

    habitability = (
        zone_score
        * temperature_score
        * type_score
    )

    return float(
        np.clip(
            habitability,
            0.0,
            1.0,
        )
    )

# =========================
# SINGLE PLANET
# =========================

def generate_planet(
    star,
    orbital_order,
    orbital_distance,
    rng,
):
    # Generate one planet around a star.

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

    habitability = generate_habitability(
        planet_type,
        temperature,
        orbital_distance,
        star,
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
        "habitability": habitability,
    }

# =========================
# PLANETS AROUND ONE STAR
# =========================

def generate_planets(star, rng):
    # Generate all planets around one star.

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

# =========================
# ALL STARS
# =========================

def generate_all_planets(stars, rng):
    # Generate planets for every generated star.

    # Returns:
    #     list[dict]

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
