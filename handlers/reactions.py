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
    elif reaction == "white_check_mark":
        _handle_resolve(client, channel, message_ts)


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


# ---------------------------------------------------------------------------
# ✅ Resolve (reacted on ticket header in ops thread)
# ---------------------------------------------------------------------------

def _handle_resolve(client, channel: str, message_ts: str):
    ticket = ticket_store.get_ticket_by_ops_thread(message_ts)
    if not ticket:
        return
    if ticket["resolved"]:
        return

    ticket_store.resolve_ticket(ticket["merchant_thread_ts"])

    client.chat_postMessage(
        channel=ticket["merchant_channel"],
        thread_ts=ticket["merchant_thread_ts"],
        text="Your support request has been resolved. Thanks for reaching out to Breeze Customer Support! :white_check_mark: If you have further questions, feel free to tag @Breeze Customer Support in a new message.",
    )

    client.chat_postMessage(
        channel=ticket["ops_channel"],
        thread_ts=ticket["ops_thread_ts"],
        text=":white_check_mark: *Ticket resolved.* Merchant has been notified.",
    )

    try:
        client.reactions_add(channel=channel, name="white_check_mark", timestamp=message_ts)
    except Exception:
        pass
