import os


def log_error(client, context: str, error: Exception, extra: dict = None):
    ops_channel = os.environ.get("OPS_CHANNEL_ID")
    if not ops_channel:
        print(f"ERROR [{context}]: {error}")
        return

    lines = [f":warning: *Bot Error — {context}*"]

    if extra:
        if extra.get("merchant_channel"):
            lines.append(f">*Merchant channel:* <#{extra['merchant_channel']}>")
        if extra.get("ops_thread_ts") and extra.get("ops_channel"):
            thread_url = f"https://slack.com/archives/{extra['ops_channel']}/p{extra['ops_thread_ts'].replace('.', '')}"
            lines.append(f">*Ticket thread:* {thread_url}")
        if extra.get("message"):
            lines.append(f">*Message:* {extra['message'][:200]}")

    lines.append(f"```{type(error).__name__}: {error}```")

    try:
        client.chat_postMessage(
            channel=ops_channel,
            text="\n".join(lines),
            unfurl_links=False,
        )
    except Exception as e:
        print(f"ERROR [{context}]: {error} (also failed to log to Slack: {e})")

    print(f"ERROR [{context}]: {error}")
