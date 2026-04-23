import html
import io
import os
import threading
import requests
import ticket_store
import error_logger

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
    files = event.get("files", [])

    if not thread_ts:
        return

    # Must have text or files to send
    if not message and not files:
        return

    # Find the ticket for this ops thread
    ticket = ticket_store.get_ticket_by_ops_thread(thread_ts)
    if not ticket:
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

        try:
            # Send text message if present
            if message:
                result = client.chat_postMessage(
                    channel=ticket["merchant_channel"],
                    thread_ts=ticket["merchant_thread_ts"],
                    text=message,
                )
                pending["mirrored_ts"] = result["ts"]
                pending["mirrored_channel"] = ticket["merchant_channel"]

            # Send files if present
            for file in files:
                _send_file_to_merchant(client, file, ticket["merchant_channel"], ticket["merchant_thread_ts"], agent_name)
        except Exception as e:
            error_logger.log_error(client, "Send — failed to send message to merchant", e)

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
        "files": files,
    })
    timer.start()


def _send_file_to_merchant(client, file: dict, merchant_channel: str, merchant_thread_ts: str, agent_name: str):
    url_private = file.get("url_private")
    name = file.get("name", "file")
    filetype = file.get("filetype", "")

    if not url_private:
        return

    try:
        token = os.environ["SLACK_BOT_TOKEN"]
        resp = requests.get(url_private, headers={"Authorization": f"Bearer {token}"})
        if resp.status_code != 200:
            return

        client.files_upload_v2(
            channel=merchant_channel,
            thread_ts=merchant_thread_ts,
            file=io.BytesIO(resp.content),
            filename=name,
            initial_comment="",
        )
    except Exception as e:
        print(f"File send error: {type(e).__name__}: {e}")


def _get_display_name(client, user: str) -> str:
    try:
        info = client.users_info(user=user)
        profile = info["user"]["profile"]
        return profile.get("display_name") or info["user"]["real_name"]
    except Exception:
        return user
