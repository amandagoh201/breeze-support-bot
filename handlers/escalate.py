import os
import ticket_store


def handle_mention(event: dict, client, say):
    OPS_CHANNEL = os.environ["OPS_CHANNEL_ID"]
    channel = event["channel"]
    ts = event["ts"]
    thread_ts = event.get("thread_ts", ts)
    user = event.get("user", "unknown")
    text = event.get("text", "")

    # Ignore if ticket already exists for this thread
    if ticket_store.get_ticket_by_merchant_thread(thread_ts):
        return

    # Auto-reply in merchant thread
    say(
        text="Thanks for reaching out! A support agent will be with you soon. Feel free to add any additional details in this thread.",
        thread_ts=thread_ts,
    )

    # Post ticket header in ops channel
    ticket_text = (
        f":ticket: *New Support Ticket*\n"
        f">*From:* <@{user}>\n"
        f">*Channel:* <#{channel}>\n"
        f">*Message:* {text}\n"
        f">*Thread:* https://slack.com/archives/{channel}/p{thread_ts.replace('.', '')}\n\n"
        f"_Reply here for internal discussion. Start a message with `send:` to reply to merchant. React :wastebasket: on a sent message to recall it._"
    )

    result = client.chat_postMessage(
        channel=OPS_CHANNEL,
        text=ticket_text,
        unfurl_links=False,
    )
    ops_thread_ts = result["ts"]

    ticket_store.create_ticket(
        merchant_channel=channel,
        merchant_thread_ts=thread_ts,
        ops_channel=OPS_CHANNEL,
        ops_thread_ts=ops_thread_ts,
    )
