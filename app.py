import os
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from dotenv import load_dotenv

import handlers.escalate as escalate
import handlers.mirror as mirror
import handlers.reactions as reactions
import handlers.send as send

load_dotenv()

app = App(token=os.environ["SLACK_BOT_TOKEN"])

OPS_CHANNEL = os.environ["OPS_CHANNEL_ID"]


@app.event("app_mention")
def on_mention(event, client, say):
    channel = event["channel"]
    user = event["user"]
    text = event.get("text", "").lower()

    # Internal agent typing "@Breeze Customer Support commands" — works in any channel
    if "commands" in text and _is_internal_user(client, user):
        try:
            result = client.chat_postEphemeral(
                channel=channel,
                user=user,
                text=(
                    "*Breeze Customer Support — Agent Commands*\n\n"
                    "`send: <message>` — sends your message to the merchant thread (30s countdown before sending)\n"
                    "React ❌ on a `send:` message — cancels the send during the countdown\n"
                    "React ✅ on a ticket header in the ops channel — marks ticket as resolved and notifies the merchant\n\n"
                    "_Emojis added automatically by the bot:_\n"
                    "⏳ countdown in progress  |  📬 message sent\n\n"
                    "React 🗑️ on a `send:` message after sending — recalls (deletes) it from the merchant thread"
                ),
            )
        except Exception as e:
            print(f"Error sending commands ephemeral: {e}")
        return

    # Ignore other mentions from the ops channel
    if channel == OPS_CHANNEL:
        try:
            client.chat_postEphemeral(
                channel=channel,
                user=user,
                text="Hey! This is the internal ops channel. Did you mean to escalate from a merchant channel?",
                thread_ts=event.get("thread_ts", event["ts"]),
            )
        except Exception:
            pass
        return

    escalate.handle_mention(event, client, say)


@app.event("message")
def on_message(event, client):
    # Ignore bot messages and all subtypes except file_share
    subtype = event.get("subtype")
    if event.get("bot_id") or (subtype and subtype != "file_share"):
        return

    channel = event.get("channel")
    thread_ts = event.get("thread_ts")

    if not thread_ts:
        return

    if channel == OPS_CHANNEL:
        # Check for >> prefix → outbound send flow
        send.handle_outbound_message(event, client)
    else:
        # Mirror merchant/agent thread messages to ops
        mirror.handle_thread_message(event, client)


@app.event("reaction_added")
def on_reaction_added(event, client):
    reactions.handle_reaction_added(event, client)


@app.event("app_home_opened")
def on_app_home_opened(event, client):
    client.views_publish(
        user_id=event["user"],
        view={
            "type": "home",
            "blocks": [
                {
                    "type": "header",
                    "text": {"type": "plain_text", "text": "Breeze Customer Support Bot"}
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "This bot handles merchant support escalations entirely within Slack — no external dashboard needed."
                    }
                },
                {"type": "divider"},
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "*For merchants*\n• Tag *@Breeze Customer Support* in your channel to reach a support agent\n• Add follow-up details by replying in the same thread — no need to tag again\n• You'll be notified in the thread once your request is resolved"
                    }
                },
                {"type": "divider"},
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "*For support agents*\nAll escalations land in the internal ops channel as a ticket thread. Use the following to manage each ticket:\n\n*Sending a reply to the merchant:*\nStart your message with `send:` in the ops thread — e.g. `send: your payout has been processed`\n• Bot adds ⏳ and starts a 30-second countdown before sending\n• React ❌ on the message during the countdown to cancel\n• Once sent, the message shows 📬\n• React 🗑️ on the message to recall (delete) it from the merchant thread\n\n*Resolving a ticket:*\nReact ✅ on the ticket header — merchant is notified automatically"
                    }
                },
                {"type": "divider"},
                {
                    "type": "context",
                    "elements": [
                        {
                            "type": "mrkdwn",
                            "text": "Questions about this bot? Reach out to the Breeze eng team."
                        }
                    ]
                }
            ]
        }
    )


def _is_internal_user(client, user_id: str) -> bool:
    try:
        info = client.users_info(user=user_id)
        user = info["user"]
        return not user.get("is_stranger") and not user.get("is_restricted") and not user.get("deleted")
    except Exception:
        return False


if __name__ == "__main__":
    # Resolve bot user ID for filtering self-messages in mirror handler
    bot_info = app.client.auth_test()
    mirror.set_bot_user_id(bot_info["user_id"])

    handler = SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"])
    handler.start()
