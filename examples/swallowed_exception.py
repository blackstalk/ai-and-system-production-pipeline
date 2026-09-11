# INTENTIONALLY VULNERABLE EXAMPLE — do not import into app/.
# See examples/README.md.
#
# Defect class: Swallowed Exception / Weak Failure Handling (Reliability)
#
# The bare `except: pass` silently discards ALL exceptions — including
# unrelated bugs like AttributeError or KeyError — and reports success
# to the caller even though the payment was never charged. In
# production this manifests as "orders that silently never got
# charged" with no log line, no metric, and no alert: the failure is
# invisible until a customer or finance team notices. A correct AI or
# human reviewer should flag this HIGH, and CRITICAL if payments are
# involved (a high-risk area per prompts/code-review.md).


def charge_customer_UNSAFE(payment_client, customer_id: str, amount_cents: int) -> bool:
    try:
        payment_client.charge(customer_id, amount_cents)
        return True
    except Exception:
        pass  # BUG: failure is invisible; caller thinks it succeeded
    return True


# --- Correct remediation ---------------------------------------------------
def charge_customer_SAFE(payment_client, customer_id: str, amount_cents: int) -> bool:
    try:
        payment_client.charge(customer_id, amount_cents)
        return True
    except PaymentDeclinedError:
        return False
    except PaymentGatewayError:
        raise  # let the caller retry / alert — do not pretend this succeeded


class PaymentDeclinedError(Exception):
    pass


class PaymentGatewayError(Exception):
    pass
