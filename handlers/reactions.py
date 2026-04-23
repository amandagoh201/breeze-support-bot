import ticket_store


def handle_reaction_added(event: dict, client):
    reaction = event["reaction"]
    item = event.get("item", {})

    if item.get("type") != "message":
        return

    channel = item["channel"]
    message_ts = item["ts"]

    if reaction == "x":
        _handle_cancel(client, channel, message_ts)
    elif reaction == "wastebasket":
        _handle_recall(client, channel, message_ts)


# ---------------------------------------------------------------------------
# ❌ Cancel (during 30s countdown)
# ---------------------------------------------------------------------------

def _handle_cancel(client, channel: str, message_ts: str):
    pending = ticket_store.get_pending_send(message_ts)
    if not pending:
        return

    pending["timer"].cancel()
    ticket_store.remove_pending_send(message_ts)

    try:
        client.reactions_remove(channel=channel, name="hourglass_flowing_sand", timestamp=message_ts)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# 🗑️ Recall (delete sent message from merchant thread)
# ---------------------------------------------------------------------------

def _handle_recall(client, channel: str, message_ts: str):
    pending = ticket_store.get_pending_send(message_ts)
    if not pending or "mirrored_ts" not in pending:
        return

    try:
        client.chat_delete(
            channel=pending["mirrored_channel"],
            ts=pending["mirrored_ts"],
        )
        client.reactions_remove(channel=channel, name="mailbox_with_mail", timestamp=message_ts)
        client.reactions_add(channel=channel, name="wastebasket", timestamp=message_ts)
    except Exception as e:
        print(f"Recall error: {e}")

    ticket_store.remove_pending_send(message_ts)
