from __future__ import annotations

import logging

from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

from config.settings import get_settings
from service.doc_qa_service import ask_doc
from service.qa_service import ask
from service.router_service import route_question


logger = logging.getLogger(__name__)


def trim_reply(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 20].rstrip() + "\n... (truncated)"


def build_reply(question: str) -> str:
    settings = get_settings()
    route = route_question(question)

    if route == "structured":
        result = ask(question)
        return trim_reply(result["answer_text"], settings.slack_max_reply_chars)

    if route == "document":
        result = ask_doc(question)
        return trim_reply(result["answer_text"], settings.slack_max_reply_chars)

    structured_result = ask(question)
    document_result = ask_doc(question)
    combined = (
        "[Structured Data]\n"
        f"{structured_result['answer_text']}\n\n"
        "[Document Context]\n"
        f"{document_result['answer_text']}"
    )
    return trim_reply(combined, settings.slack_max_reply_chars)


def build_app() -> App:
    settings = get_settings()
    if not settings.slack_bot_token:
        raise ValueError("SLACK_BOT_TOKEN is not configured.")

    app = App(token=settings.slack_bot_token)

    @app.event("message")
    def handle_dm_messages(body, say, logger):
        event = body.get("event", {})
        if event.get("channel_type") != "im":
            return
        if event.get("subtype") == "bot_message":
            return

        question = (event.get("text") or "").strip()
        if not question:
            say("질문 내용을 보내주세요.")
            return

        try:
            say(build_reply(question))
        except Exception as exc:
            logger.exception("Failed to answer DM question.")
            say(f"질의 처리 중 오류가 발생했습니다: {exc}")

    @app.event("app_mention")
    def handle_mentions(body, say, logger):
        event = body.get("event", {})
        question = (event.get("text") or "").strip()
        question = " ".join(part for part in question.split() if not part.startswith("<@"))

        if not question:
            say("질문 내용을 멘션과 함께 보내주세요.")
            return

        try:
            say(build_reply(question))
        except Exception as exc:
            logger.exception("Failed to answer app mention.")
            say(f"질의 처리 중 오류가 발생했습니다: {exc}")

    return app


def main():
    logging.basicConfig(level=logging.INFO)
    settings = get_settings()
    if not settings.slack_app_token:
        raise ValueError("SLACK_APP_TOKEN is not configured.")

    app = build_app()
    logger.info("Starting Slack Socket Mode app.")
    SocketModeHandler(app, settings.slack_app_token).start()


if __name__ == "__main__":
    main()
