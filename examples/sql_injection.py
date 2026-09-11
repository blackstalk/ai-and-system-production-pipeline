# INTENTIONALLY VULNERABLE EXAMPLE — do not import into app/.
# See examples/README.md.
#
# Vulnerability: SQL Injection (CWE-89)
#
# `item_id` is spliced directly into the query string. An attacker who
# controls `item_id` can inject arbitrary SQL, e.g.
#   item_id = "1 OR 1=1; DROP TABLE items;--"
# A correct AI or human reviewer should flag this CRITICAL and require
# parameterized queries.

import sqlite3


def get_item_by_id_UNSAFE(connection: sqlite3.Connection, item_id: str):
    query = f"SELECT * FROM items WHERE id = '{item_id}'"  # noqa: S608 (intentional)
    cursor = connection.execute(query)
    return cursor.fetchone()


# --- Correct remediation ---------------------------------------------------
def get_item_by_id_SAFE(connection: sqlite3.Connection, item_id: str):
    query = "SELECT * FROM items WHERE id = ?"
    cursor = connection.execute(query, (item_id,))
    return cursor.fetchone()
