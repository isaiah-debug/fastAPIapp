import sqlite3
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
DATABASE_PATH = BASE_DIR / "app.db"


def get_connection() -> sqlite3.Connection:
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def create_database() -> None:
    with get_connection() as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                age INTEGER NOT NULL CHECK (age >= 0)
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                text TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
            """
        )
        seed_database(connection)


def seed_database(connection: sqlite3.Connection) -> None:
    users = [
        ("ada", 36),
        ("grace", 44),
        ("alan", 41),
    ]
    connection.executemany(
        "INSERT OR IGNORE INTO users (username, age) VALUES (?, ?)",
        users,
    )

    message_count = connection.execute("SELECT COUNT(*) FROM messages").fetchone()[0]
    if message_count:
        return

    seeded_messages = [
        ("ada", "The first rule of web apps: save the data somewhere sturdy."),
        ("grace", "FastAPI plus SQLite makes a very friendly lab stack."),
        ("alan", "Templates turn database rows into pages people can read."),
    ]
    for username, text in seeded_messages:
        user_id = connection.execute(
            "SELECT id FROM users WHERE username = ?",
            (username,),
        ).fetchone()["id"]
        connection.execute(
            "INSERT INTO messages (user_id, text) VALUES (?, ?)",
            (user_id, text),
        )


if __name__ == "__main__":
    create_database()
    print(f"Created database at {DATABASE_PATH}")
