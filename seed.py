"""Build demo.db from the Google Government Content Removals dataset.

Source JSON: ../krMaynard.github.io/data/google-government-removals.json

The source is a column-store-ish format: lookup arrays (periods, countries,
requestors, products, reasons) and a `rows` array where the first five
columns are indices into those lookups and the rest are integer counts.
We expand it into a small star schema: dimension tables + a `removals`
fact table with foreign keys.
"""
import json
import os
import sqlite3

HERE = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(HERE, "demo.db")
SOURCE_JSON = os.path.normpath(
    os.path.join(HERE, "..", "krMaynard.github.io", "data", "google-government-removals.json")
)


def main() -> None:
    with open(SOURCE_JSON, "r", encoding="utf-8") as f:
        data = json.load(f)

    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.executescript(
        """
        CREATE TABLE periods (
            id INTEGER PRIMARY KEY,
            label TEXT NOT NULL UNIQUE
        );
        CREATE TABLE countries (
            id INTEGER PRIMARY KEY,
            code TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL
        );
        CREATE TABLE requestors (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL UNIQUE
        );
        CREATE TABLE products (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL UNIQUE
        );
        CREATE TABLE reasons (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL UNIQUE
        );
        CREATE TABLE removals (
            id INTEGER PRIMARY KEY,
            period_id INTEGER NOT NULL REFERENCES periods(id),
            country_id INTEGER NOT NULL REFERENCES countries(id),
            requestor_id INTEGER NOT NULL REFERENCES requestors(id),
            product_id INTEGER NOT NULL REFERENCES products(id),
            reason_id INTEGER NOT NULL REFERENCES reasons(id),
            num_requests INTEGER NOT NULL,
            items_requested INTEGER NOT NULL,
            removed_legal INTEGER NOT NULL,
            removed_policy INTEGER NOT NULL,
            not_found INTEGER NOT NULL,
            not_enough_info INTEGER NOT NULL,
            no_action INTEGER NOT NULL,
            already_removed INTEGER NOT NULL
        );
        CREATE INDEX idx_removals_period ON removals(period_id);
        CREATE INDEX idx_removals_country ON removals(country_id);
        CREATE INDEX idx_removals_product ON removals(product_id);
        CREATE INDEX idx_removals_reason ON removals(reason_id);
        """
    )

    cur.executemany(
        "INSERT INTO periods (id, label) VALUES (?, ?)",
        [(i, label) for i, label in enumerate(data["periods"])],
    )
    cur.executemany(
        "INSERT INTO countries (id, code, name) VALUES (?, ?, ?)",
        [
            (i, code, name)
            for i, (code, name) in enumerate(zip(data["countries"], data["country_names"]))
        ],
    )
    cur.executemany(
        "INSERT INTO requestors (id, name) VALUES (?, ?)",
        [(i, name) for i, name in enumerate(data["requestors"])],
    )
    cur.executemany(
        "INSERT INTO products (id, name) VALUES (?, ?)",
        [(i, name) for i, name in enumerate(data["products"])],
    )
    cur.executemany(
        "INSERT INTO reasons (id, name) VALUES (?, ?)",
        [(i, name) for i, name in enumerate(data["reasons"])],
    )

    cur.executemany(
        "INSERT INTO removals (period_id, country_id, requestor_id, product_id, "
        "reason_id, num_requests, items_requested, removed_legal, removed_policy, "
        "not_found, not_enough_info, no_action, already_removed) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        data["rows"],
    )

    conn.commit()
    cur.execute("SELECT COUNT(*) FROM removals")
    (n_rows,) = cur.fetchone()
    conn.close()

    print(
        f"Seeded {DB_PATH}: {n_rows} removal rows across "
        f"{len(data['periods'])} periods, {len(data['countries'])} countries, "
        f"{len(data['products'])} products, {len(data['reasons'])} reasons."
    )


if __name__ == "__main__":
    main()
