import sqlite3
from contextlib import contextmanager
from typing import List, Tuple, Optional

import config

DB_FILE: str = config.STORAGE_LOCATION


@contextmanager
def connect_db():
    con = sqlite3.connect(DB_FILE)
    try:
        con.execute("PRAGMA foreign_keys = ON;")
        yield con
        con.commit()
    finally:
        con.close()


def init_db() -> None:
    # Initialize DB tables if they don't exist
    with connect_db() as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS menu_item (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE
            );
        """)

        con.execute("""
            CREATE TABLE IF NOT EXISTS ingredient (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                menu_item_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                counter INTEGER NOT NULL,
                UNIQUE(menu_item_id, name),
                FOREIGN KEY(menu_item_id) REFERENCES menu_item(id) ON DELETE CASCADE
            );
        """)

# ----------------------------
def add_menu_item(name: str) -> None:
    """Add menu item if missing; do nothing if it already exists."""
    with connect_db() as con:
        con.execute("INSERT OR IGNORE INTO menu_item(name) VALUES (?);", (name,))

#def blklist_menu_item(name: str) -> None:

def menu_item_exists(name: str) -> bool:
    with connect_db() as con:
        row = con.execute("SELECT 1 FROM menu_item WHERE name = ?;", (name,)).fetchone()
        return row is not None


# ----------------------------
# Ingredient helpers
# ----------------------------

def _get_menu_item_id(con: sqlite3.Connection, menu_item_name: str) -> int:
    row = con.execute("SELECT id FROM menu_item WHERE name = ?;", (menu_item_name,)).fetchone()
    if not row:
        raise KeyError(f"Menu item '{menu_item_name}' not found.")
    return int(row[0])


def add_ingredient_or_increment(menu_item_name: str, ingredient_name: str, amount: int = 1) -> None:
    """
    If the ingredient exists, add 'amount' to the counter.
    If it doesn't exist, create it with 'amount' as the starting value.
    """
    with connect_db() as con:
        # Get the ID for the parent menu item
        menu_item_id = _get_menu_item_id(con, menu_item_name)
        
        # Perform the "Upsert"
        con.execute("""
            INSERT INTO ingredient(menu_item_id, name, counter)
            VALUES (?, ?, ?)
            ON CONFLICT(menu_item_id, name)
            DO UPDATE SET counter = counter + excluded.counter;
        """, (menu_item_id, ingredient_name, amount))


def set_counter(menu_item_name: str, ingredient_name: str, value: int) -> None:
    if value < 0:
        raise ValueError("value must be >= 0")
    with connect_db() as con:
        menu_item_id = _get_menu_item_id(con, menu_item_name)
        cur = con.execute(
            "UPDATE ingredient SET counter = ? WHERE menu_item_id = ? AND name = ?;",
            (int(value), menu_item_id, ingredient_name),
        )
        if cur.rowcount == 0:
            raise KeyError(f"Ingredient '{ingredient_name}' not found under '{menu_item_name}'.")

def get_counter(menu_item_name: str, ingredient_name: str) -> int:
    with connect_db() as con:
        menu_item_id = _get_menu_item_id(con, menu_item_name)
        row = con.execute(
            "SELECT counter FROM ingredient WHERE menu_item_id = ? AND name = ?;",
            (menu_item_id, ingredient_name),
        ).fetchone()
        if not row:
            raise KeyError(f"Ingredient '{ingredient_name}' not found under '{menu_item_name}'.")
        return int(row[0])


def ingredient_exists(menu_item_name: str, ingredient_name: str) -> bool:
    with connect_db() as con:
        try:
            menu_item_id = _get_menu_item_id(con, menu_item_name)
        except KeyError:
            return False
        row = con.execute(
            "SELECT 1 FROM ingredient WHERE menu_item_id = ? AND name = ?;",
            (menu_item_id, ingredient_name),
        ).fetchone()
        return row is not None


def list_ingredients(menu_item_name: str) -> List[Tuple[str, int]]:
    with connect_db() as con:
        rows = con.execute("""
            SELECT i.name, i.counter
              FROM ingredient i
              JOIN menu_item m ON m.id = i.menu_item_id
             WHERE m.name = ?
             ORDER BY i.name;
        """, (menu_item_name,)).fetchall()
        return [(r[0], int(r[1])) for r in rows]