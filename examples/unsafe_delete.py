# INTENTIONALLY VULNERABLE EXAMPLE — do not import into app/.
# See examples/README.md.
#
# Defect class: Destructive Operation Without Safeguards
#
# This endpoint permanently and irreversibly deletes ALL of a user's
# data with a single unauthenticated-feeling GET request, no
# confirmation step, no soft-delete/undo window, and no audit log
# entry. GET requests can also be triggered by link prefetching, CSRF,
# or crawlers, so using GET for a destructive action is itself a bug.
# A correct AI or human reviewer should flag this CRITICAL — it touches
# both "destructive operations" and "data deletion", both called out as
# high-risk areas in prompts/code-review.md.


from fastapi import APIRouter

router = APIRouter()


@router.get("/users/{user_id}/purge")
def purge_user_data_UNSAFE(user_id: str, db):
    db.execute("DELETE FROM orders WHERE user_id = ?", (user_id,))
    db.execute("DELETE FROM addresses WHERE user_id = ?", (user_id,))
    db.execute("DELETE FROM users WHERE id = ?", (user_id,))
    return {"status": "deleted"}


# --- Correct remediation ---------------------------------------------------
# 1. Use POST/DELETE, not GET, for a destructive action.
# 2. Require explicit confirmation (e.g. a re-typed resource name or a
#    signed confirmation token) and authorization (only the account
#    owner or an admin with an audited reason).
# 3. Soft-delete first (mark records deleted, retain for N days) rather
#    than hard-deleting immediately, so mistakes are recoverable.
# 4. Write an audit log entry with who requested the deletion and why.
@router.post("/users/{user_id}/purge")
def purge_user_data_SAFE(user_id: str, confirmation_token: str, current_user: dict, db, audit_log):
    if current_user["id"] != user_id and not current_user.get("is_admin"):
        raise PermissionError("not authorized to purge this user's data")
    if not _confirmation_token_is_valid(user_id, confirmation_token):
        raise ValueError("invalid or expired confirmation token")

    db.execute(
        "UPDATE users SET deleted_at = now(), pending_purge = true WHERE id = ?",
        (user_id,),
    )
    audit_log.record(actor=current_user["id"], action="soft_delete_requested", target=user_id)
    return {"status": "scheduled_for_deletion", "recoverable_until_days": 30}


def _confirmation_token_is_valid(user_id: str, token: str) -> bool:
    raise NotImplementedError("example stub")
