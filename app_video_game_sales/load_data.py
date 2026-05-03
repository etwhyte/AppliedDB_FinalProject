"""
Author: Evan Whyte
Purpose: Load the raw my_vgsales.csv file into a normalized SQLite database.
"""

import sqlite3

import pandas as pd


DB_PATH = "vgames.db"
CSV_PATH = "Data\my_vgsales.csv"


def clean_value(value):
    """Return None for blank/NaN values, otherwise return the original value."""
    if pd.isna(value):
        return None
    if isinstance(value, str) and value.strip() == "":
        return None
    return value


def main():

    df = pd.read_csv(CSV_PATH)

    df = df.dropna(subset=["Name", "Platform", "Genre", "Publisher", "Global_Sales"]).copy()

    df["Year"] = pd.to_numeric(df["Year"], errors="coerce").astype("Int64")

    for col in ["NA_Sales", "EU_Sales", "JP_Sales", "Other_Sales", "Global_Sales"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON;")
    cur = conn.cursor()

    cur.executescript(
        """
        DROP TABLE IF EXISTS games;
        DROP TABLE IF EXISTS platforms;
        DROP TABLE IF EXISTS genres;
        DROP TABLE IF EXISTS publishers;
        DROP TABLE IF EXISTS vg_sales_raw;

        CREATE TABLE vg_sales_raw (
            rank INTEGER,
            name TEXT,
            platform TEXT,
            year INTEGER,
            genre TEXT,
            publisher TEXT,
            na_sales REAL,
            eu_sales REAL,
            jp_sales REAL,
            other_sales REAL,
            global_sales REAL
        );

        CREATE TABLE platforms (
            platform_id INTEGER PRIMARY KEY AUTOINCREMENT,
            platform_name TEXT NOT NULL UNIQUE
        );

        CREATE TABLE genres (
            genre_id INTEGER PRIMARY KEY AUTOINCREMENT,
            genre_name TEXT NOT NULL UNIQUE
        );

        CREATE TABLE publishers (
            publisher_id INTEGER PRIMARY KEY AUTOINCREMENT,
            publisher_name TEXT NOT NULL UNIQUE
        );

        CREATE TABLE games (
            game_id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            release_year INTEGER,
            platform_id INTEGER NOT NULL,
            genre_id INTEGER NOT NULL,
            publisher_id INTEGER NOT NULL,
            na_sales REAL NOT NULL DEFAULT 0,
            eu_sales REAL NOT NULL DEFAULT 0,
            jp_sales REAL NOT NULL DEFAULT 0,
            other_sales REAL NOT NULL DEFAULT 0,
            global_sales REAL NOT NULL DEFAULT 0,
            FOREIGN KEY (platform_id) REFERENCES platforms(platform_id),
            FOREIGN KEY (genre_id) REFERENCES genres(genre_id),
            FOREIGN KEY (publisher_id) REFERENCES publishers(publisher_id),
            CHECK (global_sales >= 0),
            CHECK (na_sales >= 0),
            CHECK (eu_sales >= 0),
            CHECK (jp_sales >= 0),
            CHECK (other_sales >= 0),
            CHECK (release_year IS NULL OR release_year BETWEEN 1970 AND 2035)
        );
        """
    )

    raw_cols = {
        "Rank": "rank",
        "Name": "name",
        "Platform": "platform",
        "Year": "year",
        "Genre": "genre",
        "Publisher": "publisher",
        "NA_Sales": "na_sales",
        "EU_Sales": "eu_sales",
        "JP_Sales": "jp_sales",
        "Other_Sales": "other_sales",
        "Global_Sales": "global_sales",
    }
    df.rename(columns=raw_cols)[list(raw_cols.values())].to_sql(
        "vg_sales_raw", conn, if_exists="append", index=False
    )

    cur.execute(
        """
        INSERT INTO platforms (platform_name)
        SELECT DISTINCT platform
        FROM vg_sales_raw
        WHERE platform IS NOT NULL;
        """
    )
    cur.execute(
        """
        INSERT INTO genres (genre_name)
        SELECT DISTINCT genre
        FROM vg_sales_raw
        WHERE genre IS NOT NULL;
        """
    )
    cur.execute(
        """
        INSERT INTO publishers (publisher_name)
        SELECT DISTINCT publisher
        FROM vg_sales_raw
        WHERE publisher IS NOT NULL;
        """
    )

    cur.execute(
        """
        INSERT INTO games (
            title,
            release_year,
            platform_id,
            genre_id,
            publisher_id,
            na_sales,
            eu_sales,
            jp_sales,
            other_sales,
            global_sales
        )
        SELECT
            r.name,
            r.year,
            p.platform_id,
            g.genre_id,
            pu.publisher_id,
            r.na_sales,
            r.eu_sales,
            r.jp_sales,
            r.other_sales,
            r.global_sales
        FROM vg_sales_raw r
        JOIN platforms p ON r.platform = p.platform_name
        JOIN genres g ON r.genre = g.genre_name
        JOIN publishers pu ON r.publisher = pu.publisher_name;
        """
    )

    conn.commit()

    totals = cur.execute(
        """
        SELECT
            (SELECT COUNT(*) FROM games) AS games,
            (SELECT COUNT(*) FROM platforms) AS platforms,
            (SELECT COUNT(*) FROM genres) AS genres,
            (SELECT COUNT(*) FROM publishers) AS publishers;
        """
    ).fetchone()

    conn.close()
    print("Database created successfully.")
    print(f"Games: {totals[0]}, Platforms: {totals[1]}, Genres: {totals[2]}, Publishers: {totals[3]}")


if __name__ == "__main__":
    main()
