# INTENTIONALLY VULNERABLE EXAMPLE — do not import into app/.
# See examples/README.md.
#
# Defect class: N+1 Query / Unbounded Workload (Performance)
#
# For a list of N orders, this issues 1 query to fetch orders plus N
# additional queries (one per order) to fetch each order's line items.
# At small scale this is invisible in tests; in production with
# thousands of orders it turns a single request into thousands of
# round-trips to the database, a classic source of P99 latency spikes
# and database saturation. A correct AI or human reviewer should flag
# this MEDIUM-to-HIGH depending on the expected scale of `orders`.


def list_orders_with_items_UNSAFE(db, user_id: str) -> list[dict]:
    orders = db.query("SELECT * FROM orders WHERE user_id = ?", (user_id,))
    for order in orders:
        # One extra round-trip per order — O(N) queries.
        order["items"] = db.query(
            "SELECT * FROM order_items WHERE order_id = ?", (order["id"],)
        )
    return orders


# --- Correct remediation ---------------------------------------------------
def list_orders_with_items_SAFE(db, user_id: str) -> list[dict]:
    orders = db.query("SELECT * FROM orders WHERE user_id = ?", (user_id,))
    order_ids = [order["id"] for order in orders]
    items_by_order = db.query_grouped(
        "SELECT * FROM order_items WHERE order_id IN (?)", (order_ids,)
    )
    for order in orders:
        order["items"] = items_by_order.get(order["id"], [])
    return orders
