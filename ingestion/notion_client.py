from __future__ import annotations

from dataclasses import dataclass
import logging

import requests

from config.settings import get_settings


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class NotionPageDocument:
    page_id: str
    title: str
    url: str
    last_edited_time: str | None
    markdown_content: str


def build_notion_headers() -> dict[str, str]:
    settings = get_settings()
    if not settings.notion_access_token:
        raise ValueError("NOTION_ACCESS_TOKEN is not configured.")

    return {
        "Authorization": f"Bearer {settings.notion_access_token}",
        "Notion-Version": settings.notion_version,
        "Content-Type": "application/json",
    }


def notion_get(path: str, params: dict | None = None) -> dict:
    response = requests.get(
        f"https://api.notion.com/v1{path}",
        headers=build_notion_headers(),
        params=params,
        timeout=60,
    )
    response.raise_for_status()
    return response.json()


def extract_plain_text(rich_text_items: list[dict]) -> str:
    return "".join(item.get("plain_text", "") for item in rich_text_items)


def extract_page_title(page_payload: dict) -> str:
    properties = page_payload.get("properties", {})
    for property_value in properties.values():
        if property_value.get("type") == "title":
            title = extract_plain_text(property_value.get("title", []))
            if title:
                return title
    return "Untitled"


def list_block_children(block_id: str) -> list[dict]:
    results: list[dict] = []
    next_cursor: str | None = None

    while True:
        payload = notion_get(
            f"/blocks/{block_id}/children",
            params={"page_size": 100, "start_cursor": next_cursor} if next_cursor else {"page_size": 100},
        )
        results.extend(payload.get("results", []))
        if not payload.get("has_more"):
            return results
        next_cursor = payload.get("next_cursor")


def block_to_markdown(block: dict, depth: int = 0) -> list[str]:
    block_type = block.get("type", "")
    block_value = block.get(block_type, {})
    indent = "  " * depth

    if block_type == "paragraph":
        text = extract_plain_text(block_value.get("rich_text", []))
        return [f"{indent}{text}"] if text else []
    if block_type == "heading_1":
        text = extract_plain_text(block_value.get("rich_text", []))
        return [f"# {text}"] if text else []
    if block_type == "heading_2":
        text = extract_plain_text(block_value.get("rich_text", []))
        return [f"## {text}"] if text else []
    if block_type == "heading_3":
        text = extract_plain_text(block_value.get("rich_text", []))
        return [f"### {text}"] if text else []
    if block_type == "bulleted_list_item":
        text = extract_plain_text(block_value.get("rich_text", []))
        return [f"{indent}- {text}"] if text else []
    if block_type == "numbered_list_item":
        text = extract_plain_text(block_value.get("rich_text", []))
        return [f"{indent}1. {text}"] if text else []
    if block_type == "to_do":
        text = extract_plain_text(block_value.get("rich_text", []))
        checked = "x" if block_value.get("checked") else " "
        return [f"{indent}- [{checked}] {text}"] if text else []
    if block_type == "quote":
        text = extract_plain_text(block_value.get("rich_text", []))
        return [f"{indent}> {text}"] if text else []
    if block_type == "callout":
        text = extract_plain_text(block_value.get("rich_text", []))
        return [f"{indent}> {text}"] if text else []
    if block_type == "code":
        text = extract_plain_text(block_value.get("rich_text", []))
        language = block_value.get("language", "")
        return [f"```{language}", text, "```"] if text else []
    if block_type == "toggle":
        text = extract_plain_text(block_value.get("rich_text", []))
        return [f"{indent}- {text}"] if text else []
    if block_type == "child_page":
        title = block_value.get("title", "")
        return [f"{indent}## {title}"] if title else []

    return []


def collect_markdown_lines(blocks: list[dict], depth: int = 0) -> list[str]:
    lines: list[str] = []

    for block in blocks:
        lines.extend(block_to_markdown(block, depth))

        if block.get("has_children"):
            child_lines = collect_markdown_lines(list_block_children(block["id"]), depth + 1)
            if child_lines:
                lines.extend(child_lines)

    return lines


def fetch_notion_page_document(page_id: str) -> NotionPageDocument:
    logger.info("Fetching Notion page: %s", page_id)
    page_payload = notion_get(f"/pages/{page_id}")
    blocks = list_block_children(page_id)
    markdown_lines = collect_markdown_lines(blocks)
    markdown_content = "\n\n".join(line for line in markdown_lines if line.strip()).strip()

    return NotionPageDocument(
        page_id=page_id,
        title=extract_page_title(page_payload),
        url=page_payload.get("url", ""),
        last_edited_time=page_payload.get("last_edited_time"),
        markdown_content=markdown_content,
    )
