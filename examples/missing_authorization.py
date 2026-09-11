# INTENTIONALLY VULNERABLE EXAMPLE — do not import into app/.
# See examples/README.md.
#
# Vulnerability: Broken Access Control / Missing Authorization (CWE-862)
#
# The endpoint authenticates the caller (via `current_user`) but never
# checks that `current_user` actually owns `order_id` before returning
# it — any authenticated user can read any other user's order by
# guessing/incrementing the ID (an Insecure Direct Object Reference).
# A correct AI or human reviewer should flag this CRITICAL, especially
# because it touches "personal data" — a high-risk area called out in
# prompts/code-review.md.

from fastapi import APIRouter

router = APIRouter()


@router.get("/orders/{order_id}")
def get_order_UNSAFE(order_id: str, current_user: dict):
    order = _load_order_from_db(order_id)
    return order  # BUG: never verified order.user_id == current_user["id"]


# --- Correct remediation ---------------------------------------------------
@router.get("/orders/{order_id}")
def get_order_SAFE(order_id: str, current_user: dict):
    order = _load_order_from_db(order_id)
    if order["user_id"] != current_user["id"]:
        raise PermissionError("not authorized to view this order")
    return order


def _load_order_from_db(order_id: str) -> dict:
    raise NotImplementedError("example stub")
