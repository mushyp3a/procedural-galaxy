#!/usr/bin/env python3

import os
import sqlite3

# =========================
# DATABASE
# =========================

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
                    x, y, z, density, H, He, C, O, Fe
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
                    system["Fe"],
                )
            )
            system_ids[system_index] = cursor.lastrowid
        self.connection.commit()
        return system_ids

    def save_stars(self, stars, system_ids):
        self.connection.executemany(
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
            [
                (
                    system_ids[star["system_index"]],
                    star["star_number"],
                    star["mass"],
                    star["radius"],
                    star["temperature"],
                    star["luminosity"],
                    star["metallicity"],
                    star["spectral_type"],
                )
                for star in stars
            ]
        )
        self.connection.commit()
