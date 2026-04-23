import os
import traceback


def log_error(client, context: str, error: Exception):
    ops_channel = os.environ.get("OPS_CHANNEL_ID")
    if not ops_channel:
        print(f"Error [{context}]: {error}")
        return

    error_text = (
        f":warning: *Bot Error — {context}*\n"
        f"```{traceback.format_exc().strip()}```"
    )

    try:
        client.chat_postMessage(
            channel=ops_channel,
            text=error_text,
        )
    except Exception as e:
        print(f"Failed to log error to Slack: {e}")

    print(f"Error [{context}]: {error}")
