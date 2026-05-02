from data_agent.config import Settings
from data_agent.db import fetch_all
from data_agent.llm import answer_general_chat, classify_question, generate_sql, summarize_answer
from data_agent.metadata import embed_text, search_metadata
from data_agent.sql_guard import validate_readonly_mart_sql


GENERAL_PATTERNS = (
    "안녕",
    "반가워",
    "고마워",
    "감사",
    "뭐 할 수",
    "무엇을 할 수",
    "사용법",
    "도움말",
    "너 누구",
    "소개",
    "hello",
    "hi",
    "thanks",
    "help",
)


def is_obvious_general_chat(question: str) -> bool:
    normalized = question.lower().strip()
    return any(pattern in normalized for pattern in GENERAL_PATTERNS)


def rerank_metadata(question: str, metadata: list[dict]) -> list[dict]:
    keyword_groups = [
        ("매출", ("매출", "revenue")),
        ("주문", ("주문", "order")),
        ("광고", ("광고", "ad_spend")),
    ]
    question_lower = question.lower()

    def score(item: dict) -> int:
        text = " ".join(str(item.get(key, "")) for key in ("name", "description", "expression")).lower()
        total = 0
        for question_keyword, metadata_keywords in keyword_groups:
            if question_keyword in question_lower and any(keyword in text for keyword in metadata_keywords):
                total += 10
        return total

    return sorted(metadata, key=score, reverse=True)


def answer_question(settings: Settings, question: str) -> str:
    if is_obvious_general_chat(question):
        return answer_general_chat(settings, question)

    if classify_question(settings, question) != "data":
        return answer_general_chat(settings, question)

    question_embedding = embed_text(settings, question)
    metadata = search_metadata(settings.database_url, question_embedding)
    metadata = rerank_metadata(question, metadata)
    sql = generate_sql(settings, question, metadata)
    safe_sql = validate_readonly_mart_sql(sql)
    rows = fetch_all(settings.database_url, safe_sql)
    return summarize_answer(settings, question, safe_sql, rows)
