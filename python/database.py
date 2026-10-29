#!/usr/bin/env python3

import os
import sqlite3

# database

class Database:

    path = ""

    def __init__(self, path):
        self.path = path

        if os.path.exists(self.path):
            os.remove(self.path)

        self.connection = sqlite3.connect(path)
        self.connection.execute("PRAGMA foreign_keys = ON")

    def initialise(self):
        with open("schema.sql", "r") as file:
            schema = file.read()

        self.connection.executescript(schema)
        self.connection.commit()

    def close(self):
        self.connection.close()

    def save_systems(self, systems):
        system_ids = {}
        for system_index, system in enumerate(systems):
            cursor = self.connection.execute(
                """
                INSERT INTO systems (
                    x, y, z, density, H, He, C, O, metallicity
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    system["x"],
                    system["y"],
                    system["z"],
                    system["density"],
                    system["H"],
                    system["He"],
                    system["C"],
                    system["O"],
                    system["metallicity"],
                ),
            )
            system_ids[system_index] = cursor.lastrowid
        self.connection.commit()
        return system_ids

    def save_stars(self, stars, system_ids):
        star_ids = {}
        for star_index, star in enumerate(stars):
            cursor = self.connection.execute(
                """
                INSERT INTO stars (
                    system_id,
                    star_number,
                    mass,
                    radius,
                    temperature,
                    luminosity,
                    metallicity,
                    spectral_type
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    system_ids[star["system_index"]],
                    star["star_number"],
                    star["mass"],
                    star["radius"],
                    star["temperature"],
                    star["luminosity"],
                    star["metallicity"],
                    star["spectral_type"],
                ),
            )
            star_ids[star_index] = cursor.lastrowid
        self.connection.commit()
        return star_ids

    def save_planets(self, planets, system_ids, star_ids):
        self.connection.executemany(
            """
            INSERT INTO planets (
                system_id,
                star_id,
                orbital_order,
                orbital_distance,
                mass,
                radius,
                temperature,
                planet_type,
                albedo
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    system_ids[planet["system_index"]],
                    star_ids[planet["star_index"]],
                    planet["orbital_order"],
                    planet["orbital_distance"],
                    planet["mass"],
                    planet["radius"],
                    planet["temperature"],
                    planet["planet_type"],
                    planet["albedo"],
                )
                for planet in planets
            ]
        )
        self.connection.commit()
