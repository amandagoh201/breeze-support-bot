import threading
from typing import Optional

_lock = threading.Lock()

# merchant_thread_ts -> ticket data
_tickets: dict[str, dict] = {}

# ops_message_ts -> merchant_thread_ts (for reaction lookups on ops messages)
_ops_to_merchant: dict[str, str] = {}

# pending sends: ops_message_ts -> {"timer": Timer, "channel": str, "text": str, "agent_name": str}
_pending_sends: dict[str, dict] = {}


def create_ticket(
    merchant_channel: str,
    merchant_thread_ts: str,
    ops_channel: str,
    ops_thread_ts: str,
):
    with _lock:
        _tickets[merchant_thread_ts] = {
            "merchant_channel": merchant_channel,
            "merchant_thread_ts": merchant_thread_ts,
            "ops_channel": ops_channel,
            "ops_thread_ts": ops_thread_ts,
            "resolved": False,
        }
        _ops_to_merchant[ops_thread_ts] = merchant_thread_ts


def get_ticket_by_merchant_thread(merchant_thread_ts: str) -> Optional[dict]:
    return _tickets.get(merchant_thread_ts)


def get_ticket_by_ops_thread(ops_thread_ts: str) -> Optional[dict]:
    merchant_ts = _ops_to_merchant.get(ops_thread_ts)
    if merchant_ts:
        return _tickets.get(merchant_ts)
    return None


def resolve_ticket(merchant_thread_ts: str):
    with _lock:
        if merchant_thread_ts in _tickets:
            _tickets[merchant_thread_ts]["resolved"] = True


def is_resolved(merchant_thread_ts: str) -> bool:
    ticket = _tickets.get(merchant_thread_ts)
    return ticket["resolved"] if ticket else False


def add_pending_send(ops_message_ts: str, data: dict):
    with _lock:
        _pending_sends[ops_message_ts] = data


def get_pending_send(ops_message_ts: str) -> Optional[dict]:
    return _pending_sends.get(ops_message_ts)


def remove_pending_send(ops_message_ts: str):
    with _lock:
        _pending_sends.pop(ops_message_ts, None)
