from __future__ import annotations

from llm.llm_client import classify_route


DOCUMENT_KEYWORDS = {
    "문서",
    "정책",
    "가이드",
    "위키",
    "회의록",
    "절차",
    "설명",
    "기준",
    "매뉴얼",
    "문맥",
    "policy",
    "guide",
    "wiki",
    "meeting note",
    "meeting notes",
    "procedure",
    "document",
    "docs",
    "manual",
}

STRUCTURED_KEYWORDS = {
    "매출",
    "광고비",
    "지출",
    "비용",
    "roas",
    "캠페인",
    "채널",
    "상품",
    "추이",
    "합계",
    "평균",
    "순위",
    "비교",
    "어제",
    "오늘",
    "최근",
    "이번 주",
    "지난 주",
    "spend",
    "revenue",
    "campaign",
    "channel",
    "product",
    "trend",
    "total",
    "sum",
    "average",
    "rank",
    "ranking",
}


def contains_any_keyword(question: str, keywords: set[str]) -> bool:
    lowered = question.lower()
    return any(keyword.lower() in lowered for keyword in keywords)


def route_question(question: str) -> str:
    has_document_signal = contains_any_keyword(question, DOCUMENT_KEYWORDS)
    has_structured_signal = contains_any_keyword(question, STRUCTURED_KEYWORDS)

    if has_document_signal and not has_structured_signal:
        return "document"
    if has_structured_signal and not has_document_signal:
        return "structured"
    if has_document_signal and has_structured_signal:
        return "hybrid"

    return classify_route(question)
