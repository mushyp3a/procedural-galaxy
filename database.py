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
        rows = [
            (
                float(system["x"]),
                float(system["y"]),
                float(system["z"]),
                float(system["density"]),
                float(system["H"]),
                float(system["He"]),
                float(system["C"]),
                float(system["O"]),
                float(system["Fe"]),
            )
            for system in systems
        ]

        self.connection.executemany(
            """
            INSERT INTO systems (
                x,
                y,
                z,
                density,
                H,
                He,
                C,
                O,
                Fe
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            rows
        )

        self.connection.commit()
