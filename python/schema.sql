PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS systems (
    id INTEGER PRIMARY KEY,

    x REAL NOT NULL,
    y REAL NOT NULL,
    z REAL NOT NULL,

    density REAL NOT NULL,
    H REAL NOT NULL,
    He REAL NOT NULL,
    C REAL NOT NULL,
    O REAL NOT NULL,
    metallicity REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS stars (
    id INTEGER PRIMARY KEY,
    system_id INTEGER NOT NULL,
    star_number INTEGER NOT NULL,

    mass REAL NOT NULL,
    radius REAL NOT NULL,
    temperature REAL NOT NULL,
    luminosity REAL NOT NULL,
    metallicity REAL NOT NULL,
    spectral_type TEXT NOT NULL,

    FOREIGN KEY (system_id)
        REFERENCES systems(id)
);

CREATE TABLE IF NOT EXISTS planets (
    id INTEGER PRIMARY KEY,
    system_id INTEGER NOT NULL,
    star_id INTEGER NOT NULL,

    orbital_order INTEGER NOT NULL,
    orbital_distance REAL NOT NULL,

    mass REAL NOT NULL,
    radius REAL NOT NULL,
    temperature REAL NOT NULL,
    planet_type TEXT NOT NULL,
    albedo REAL NOT NULL,

    FOREIGN KEY (system_id)
        REFERENCES systems(id),

    FOREIGN KEY (star_id)
        REFERENCES stars(id)
);

CREATE TABLE IF NOT EXISTS moons (
    id INTEGER PRIMARY KEY,
    planet_id INTEGER NOT NULL,

    orbital_order INTEGER NOT NULL,
    orbital_distance REAL NOT NULL,

    mass REAL NOT NULL,
    radius REAL NOT NULL,

    FOREIGN KEY (planet_id)
        REFERENCES planets(id)
);
