import html
import threading
import ticket_store

COUNTDOWN_SECONDS = 30


def handle_outbound_message(event: dict, client):
    text = html.unescape(event.get("text", ""))

    # Only act on messages starting with "send:"
    if not text.lower().startswith("send:"):
        return
    message = text[5:].strip()

    channel = event["channel"]
    ts = event["ts"]
    thread_ts = event.get("thread_ts")
    user = event.get("user")

    if not thread_ts:
        return

    # Find the ticket for this ops thread
    ticket = ticket_store.get_ticket_by_ops_thread(thread_ts)
    if not ticket:
        return

    if ticket.get("resolved"):
        return

    if not message:
        return

    agent_name = _get_display_name(client, user)

    # Add ⏳ to signal countdown
    try:
        client.reactions_add(channel=channel, name="hourglass_flowing_sand", timestamp=ts)
    except Exception:
        pass

    def send():
        pending = ticket_store.get_pending_send(ts)
        if not pending:
            return  # was cancelled

        mirrored_text = f":speech_balloon: *{agent_name}* from Breeze Support:\n{message}"

        result = client.chat_postMessage(
            channel=ticket["merchant_channel"],
            thread_ts=ticket["merchant_thread_ts"],
            text=mirrored_text,
        )

        # Store mirrored_ts so 🗑️ can recall it
        pending["mirrored_ts"] = result["ts"]
        pending["mirrored_channel"] = ticket["merchant_channel"]

        try:
            client.reactions_remove(channel=channel, name="hourglass_flowing_sand", timestamp=ts)
            client.reactions_add(channel=channel, name="mailbox_with_mail", timestamp=ts)
        except Exception:
            pass

    timer = threading.Timer(COUNTDOWN_SECONDS, send)
    ticket_store.add_pending_send(ts, {
        "timer": timer,
        "ops_channel": channel,
        "text": message,
        "agent_name": agent_name,
    })
    timer.start()


def _get_display_name(client, user: str) -> str:
    try:
        info = client.users_info(user=user)
        profile = info["user"]["profile"]
        return profile.get("display_name") or info["user"]["real_name"]
    except Exception:
        return user
