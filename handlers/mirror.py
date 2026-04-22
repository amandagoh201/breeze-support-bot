import os
import ticket_store

BOT_USER_ID = None  # set at startup from app.py


def set_bot_user_id(uid: str):
    global BOT_USER_ID
    BOT_USER_ID = uid


def handle_thread_message(event: dict, client):
    channel = event["channel"]
    thread_ts = event.get("thread_ts")
    ts = event["ts"]
    user = event.get("user")
    text = event.get("text", "")
    bot_id = event.get("bot_id")

    if not thread_ts:
        return

    # Ignore bot messages (the bot itself posting confirmations etc.)
    if bot_id or user == BOT_USER_ID:
        return

    ticket = ticket_store.get_ticket_by_merchant_thread(thread_ts)
    if not ticket:
        return
    if ticket["resolved"]:
        return

    # Determine if sender is merchant or agent
    # Agents are workspace members; merchants in shared channels appear as external users.
    # We use is_stranger / is_restricted flags, but the simplest reliable check is
    # whether the message came from the ops channel — it didn't, so the sender is in
    # the merchant channel. We distinguish by checking if user is an internal member.
    label = _get_label(client, user, channel)

    mirror_text = f"{label} {text}"

    client.chat_postMessage(
        channel=ticket["ops_channel"],
        thread_ts=ticket["ops_thread_ts"],
        text=mirror_text,
    )


def _get_label(client, user: str, channel: str) -> str:
    if not user:
        return "[Unknown]:"
    try:
        info = client.users_info(user=user)
        profile = info["user"]["profile"]
        name = profile.get("display_name") or info["user"]["real_name"]
        is_external = info["user"].get("is_stranger") or info["user"].get("is_invited_user")
        if is_external:
            return f"[Merchant - {name}]:"
        else:
            return f"[Agent - {name}, direct]:"
    except Exception:
        return f"[{user}]:"
