"""
Author: Evan Whyte
Purpose: Flask app connected to a normalized video game sales database.
"""

import sqlite3

from flask import Flask, redirect, render_template, request, url_for


app = Flask(__name__)
DB_PATH = "vgames.db"


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def get_or_create_id(conn, table, id_col, name_col, value):
    """Find or create a lookup table value and return its id."""
    value = value.strip()
    row = conn.execute(
        f"SELECT {id_col} FROM {table} WHERE {name_col} = ?",
        (value,),
    ).fetchone()

    if row:
        return row[id_col]

    cur = conn.execute(
        f"INSERT INTO {table} ({name_col}) VALUES (?)",
        (value,),
    )
    return cur.lastrowid


def get_filters(conn):
    platforms = conn.execute("SELECT platform_name FROM platforms ORDER BY platform_name").fetchall()
    genres = conn.execute("SELECT genre_name FROM genres ORDER BY genre_name").fetchall()
    publishers = conn.execute("SELECT publisher_name FROM publishers ORDER BY publisher_name").fetchall()
    years = conn.execute(
        "SELECT DISTINCT release_year FROM games WHERE release_year IS NOT NULL ORDER BY release_year DESC"
    ).fetchall()
    return platforms, genres, publishers, years


@app.route("/")
def index():
    platform = request.args.get("platform", "")
    genre = request.args.get("genre", "")
    publisher = request.args.get("publisher", "")
    year = request.args.get("year", "")
    search = request.args.get("search", "")

    query = """
        SELECT
            g.game_id,
            g.title,
            g.release_year,
            p.platform_name,
            ge.genre_name,
            pu.publisher_name,
            g.na_sales,
            g.eu_sales,
            g.jp_sales,
            g.other_sales,
            g.global_sales
        FROM games g
        JOIN platforms p ON g.platform_id = p.platform_id
        JOIN genres ge ON g.genre_id = ge.genre_id
        JOIN publishers pu ON g.publisher_id = pu.publisher_id
        WHERE 1 = 1
    """
    params = []

    if platform:
        query += " AND p.platform_name = ?"
        params.append(platform)

    if genre:
        query += " AND ge.genre_name = ?"
        params.append(genre)

    if publisher:
        query += " AND pu.publisher_name = ?"
        params.append(publisher)

    if year:
        query += " AND g.release_year = ?"
        params.append(year)

    if search:
        query += " AND g.title LIKE ?"
        params.append(f"%{search}%")

    query += " ORDER BY g.global_sales DESC LIMIT 100"

    with get_connection() as conn:
        games = conn.execute(query, params).fetchall()

        summary_query = """
            SELECT
                p.platform_name,
                COUNT(g.game_id) AS game_count,
                ROUND(SUM(g.global_sales), 2) AS total_global_sales
            FROM games g
            JOIN platforms p ON g.platform_id = p.platform_id
            JOIN genres ge ON g.genre_id = ge.genre_id
            JOIN publishers pu ON g.publisher_id = pu.publisher_id
            WHERE 1 = 1
        """
        summary_params = []

        if platform:
            summary_query += " AND p.platform_name = ?"
            summary_params.append(platform)
        if genre:
            summary_query += " AND ge.genre_name = ?"
            summary_params.append(genre)
        if publisher:
            summary_query += " AND pu.publisher_name = ?"
            summary_params.append(publisher)
        if year:
            summary_query += " AND g.release_year = ?"
            summary_params.append(year)
        if search:
            summary_query += " AND g.title LIKE ?"
            summary_params.append(f"%{search}%")

        summary_query += """
            GROUP BY p.platform_id, p.platform_name
            ORDER BY total_global_sales DESC
            LIMIT 10;
        """
        summary = conn.execute(summary_query, summary_params).fetchall()

        platforms, genres, publishers, years = get_filters(conn)

    return render_template(
        "index.html",
        games=games,
        summary=summary,
        platforms=platforms,
        genres=genres,
        publishers=publishers,
        years=years,
        selected={
            "platform": platform,
            "genre": genre,
            "publisher": publisher,
            "year": year,
            "search": search,
        },
    )


@app.route("/add", methods=["GET", "POST"])
def add_game():
    if request.method == "POST":
        title = request.form["title"].strip()
        release_year = request.form.get("release_year") or None
        platform = request.form["platform"].strip()
        genre = request.form["genre"].strip()
        publisher = request.form["publisher"].strip()
        global_sales = float(request.form.get("global_sales") or 0)
        na_sales = float(request.form.get("na_sales") or 0)
        eu_sales = float(request.form.get("eu_sales") or 0)
        jp_sales = float(request.form.get("jp_sales") or 0)
        other_sales = float(request.form.get("other_sales") or 0)

        with get_connection() as conn:
            platform_id = get_or_create_id(conn, "platforms", "platform_id", "platform_name", platform)
            genre_id = get_or_create_id(conn, "genres", "genre_id", "genre_name", genre)
            publisher_id = get_or_create_id(conn, "publishers", "publisher_id", "publisher_name", publisher)

            conn.execute(
                """
                INSERT INTO games (
                    title, release_year, platform_id, genre_id, publisher_id,
                    na_sales, eu_sales, jp_sales, other_sales, global_sales
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    title,
                    release_year,
                    platform_id,
                    genre_id,
                    publisher_id,
                    na_sales,
                    eu_sales,
                    jp_sales,
                    other_sales,
                    global_sales,
                ),
            )
            conn.commit()

        return redirect(url_for("index"))

    return render_template("game_form.html", game=None, action="Add")


@app.route("/edit/<int:game_id>", methods=["GET", "POST"])
def edit_game(game_id):
    with get_connection() as conn:
        if request.method == "POST":
            title = request.form["title"].strip()
            release_year = request.form.get("release_year") or None
            platform = request.form["platform"].strip()
            genre = request.form["genre"].strip()
            publisher = request.form["publisher"].strip()
            global_sales = float(request.form.get("global_sales") or 0)
            na_sales = float(request.form.get("na_sales") or 0)
            eu_sales = float(request.form.get("eu_sales") or 0)
            jp_sales = float(request.form.get("jp_sales") or 0)
            other_sales = float(request.form.get("other_sales") or 0)

            platform_id = get_or_create_id(conn, "platforms", "platform_id", "platform_name", platform)
            genre_id = get_or_create_id(conn, "genres", "genre_id", "genre_name", genre)
            publisher_id = get_or_create_id(conn, "publishers", "publisher_id", "publisher_name", publisher)

            conn.execute(
                """
                UPDATE games
                SET title = ?,
                    release_year = ?,
                    platform_id = ?,
                    genre_id = ?,
                    publisher_id = ?,
                    na_sales = ?,
                    eu_sales = ?,
                    jp_sales = ?,
                    other_sales = ?,
                    global_sales = ?
                WHERE game_id = ?
                """,
                (
                    title,
                    release_year,
                    platform_id,
                    genre_id,
                    publisher_id,
                    na_sales,
                    eu_sales,
                    jp_sales,
                    other_sales,
                    global_sales,
                    game_id,
                ),
            )
            conn.commit()
            return redirect(url_for("index"))

        game = conn.execute(
            """
            SELECT
                g.*,
                p.platform_name,
                ge.genre_name,
                pu.publisher_name
            FROM games g
            JOIN platforms p ON g.platform_id = p.platform_id
            JOIN genres ge ON g.genre_id = ge.genre_id
            JOIN publishers pu ON g.publisher_id = pu.publisher_id
            WHERE g.game_id = ?
            """,
            (game_id,),
        ).fetchone()

    return render_template("game_form.html", game=game, action="Edit")


@app.route("/delete/<int:game_id>", methods=["POST"])
def delete_game(game_id):
    with get_connection() as conn:
        conn.execute("DELETE FROM games WHERE game_id = ?", (game_id,))
        conn.commit()
    return redirect(url_for("index"))


@app.route("/schema")
def schema():
    with get_connection() as conn:
        counts = conn.execute(
            """
            SELECT
                (SELECT COUNT(*) FROM games) AS games,
                (SELECT COUNT(*) FROM platforms) AS platforms,
                (SELECT COUNT(*) FROM genres) AS genres,
                (SELECT COUNT(*) FROM publishers) AS publishers;
            """
        ).fetchone()

    return render_template("schema.html", counts=counts)


if __name__ == "__main__":
    app.run(debug=True)
