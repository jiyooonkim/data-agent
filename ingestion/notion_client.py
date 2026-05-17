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


def notion_post(path: str, json_body: dict | None = None) -> dict:
    response = requests.post(
        f"https://api.notion.com/v1{path}",
        headers=build_notion_headers(),
        json=json_body or {},
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


def extract_property_text(property_value: dict) -> str:
    property_type = property_value.get("type")

    if property_type == "title":
        return extract_plain_text(property_value.get("title", []))
    if property_type == "rich_text":
        return extract_plain_text(property_value.get("rich_text", []))
    if property_type == "number":
        value = property_value.get("number")
        return "" if value is None else str(value)
    if property_type == "select":
        select_value = property_value.get("select")
        return "" if not select_value else select_value.get("name", "")
    if property_type == "multi_select":
        return ", ".join(item.get("name", "") for item in property_value.get("multi_select", []))
    if property_type == "status":
        status_value = property_value.get("status")
        return "" if not status_value else status_value.get("name", "")
    if property_type == "date":
        date_value = property_value.get("date")
        if not date_value:
            return ""
        start = date_value.get("start", "")
        end = date_value.get("end", "")
        return f"{start} ~ {end}" if end else start
    if property_type == "checkbox":
        return str(property_value.get("checkbox", False))
    if property_type == "url":
        return property_value.get("url", "") or ""
    if property_type == "email":
        return property_value.get("email", "") or ""
    if property_type == "phone_number":
        return property_value.get("phone_number", "") or ""
    if property_type == "people":
        return ", ".join(person.get("name", "") for person in property_value.get("people", []))
    if property_type == "relation":
        return ", ".join(item.get("id", "") for item in property_value.get("relation", []))
    if property_type == "created_time":
        return property_value.get("created_time", "") or ""
    if property_type == "last_edited_time":
        return property_value.get("last_edited_time", "") or ""
    if property_type == "formula":
        formula = property_value.get("formula", {})
        formula_type = formula.get("type")
        if formula_type in {"string", "number", "boolean"}:
            value = formula.get(formula_type)
            return "" if value is None else str(value)
        if formula_type == "date":
            date_value = formula.get("date")
            return "" if not date_value else date_value.get("start", "")
    return ""


def build_properties_markdown(page_payload: dict) -> list[str]:
    lines: list[str] = []
    properties = page_payload.get("properties", {})

    for property_name, property_value in properties.items():
        value_text = extract_property_text(property_value).strip()
        if value_text:
            lines.append(f"- {property_name}: {value_text}")

    return lines


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


def collect_child_page_ids(blocks: list[dict]) -> list[str]:
    child_page_ids: list[str] = []

    for block in blocks:
        if block.get("type") == "child_page" and block.get("id"):
            child_page_ids.append(block["id"])

        if block.get("has_children"):
            child_page_ids.extend(collect_child_page_ids(list_block_children(block["id"])))

    return child_page_ids


def build_page_document(
    page_payload: dict,
    include_blocks: bool = True,
    blocks: list[dict] | None = None,
) -> NotionPageDocument:
    page_id = page_payload["id"]
    properties_lines = build_properties_markdown(page_payload)
    resolved_blocks = blocks if blocks is not None else (list_block_children(page_id) if include_blocks else [])
    markdown_lines = collect_markdown_lines(resolved_blocks)
    combined_lines = []

    if properties_lines:
        combined_lines.append("# Properties")
        combined_lines.extend(properties_lines)

    if markdown_lines:
        if combined_lines:
            combined_lines.append("")
        combined_lines.extend(markdown_lines)

    markdown_content = "\n\n".join(line for line in combined_lines if line.strip()).strip()

    return NotionPageDocument(
        page_id=page_id,
        title=extract_page_title(page_payload),
        url=page_payload.get("url", ""),
        last_edited_time=page_payload.get("last_edited_time"),
        markdown_content=markdown_content,
    )


def fetch_notion_page_document(page_id: str) -> NotionPageDocument:
    logger.info("Fetching Notion page: %s", page_id)
    page_payload = notion_get(f"/pages/{page_id}")
    return build_page_document(page_payload, include_blocks=True)


def fetch_notion_page_documents(
    page_id: str,
    visited_page_ids: set[str] | None = None,
) -> list[NotionPageDocument]:
    visited = visited_page_ids if visited_page_ids is not None else set()
    if page_id in visited:
        return []

    logger.info("Fetching Notion page recursively: %s", page_id)
    visited.add(page_id)

    page_payload = notion_get(f"/pages/{page_id}")
    blocks = list_block_children(page_id)
    documents = [build_page_document(page_payload, include_blocks=True, blocks=blocks)]

    for child_page_id in collect_child_page_ids(blocks):
        documents.extend(fetch_notion_page_documents(child_page_id, visited))

    return documents


def query_data_source_pages(data_source_id: str) -> list[dict]:
    rows: list[dict] = []
    next_cursor: str | None = None

    while True:
        body = {"page_size": 100}
        if next_cursor:
            body["start_cursor"] = next_cursor

        payload = notion_post(f"/data_sources/{data_source_id}/query", body)
        results = payload.get("results", [])
        rows.extend(item for item in results if item.get("object") == "page")

        if not payload.get("has_more"):
            return rows

        next_cursor = payload.get("next_cursor")


def fetch_notion_database_documents(target_id: str) -> list[NotionPageDocument]:
    logger.info("Fetching Notion database/data source: %s", target_id)

    data_source_ids: list[str] = []

    try:
        database_payload = notion_get(f"/databases/{target_id}")
        data_source_ids = [item["id"] for item in database_payload.get("data_sources", []) if item.get("id")]
    except requests.HTTPError as exc:
        if exc.response is None or exc.response.status_code != 404:
            raise

    if not data_source_ids:
        data_source_payload = notion_get(f"/data_sources/{target_id}")
        data_source_ids = [data_source_payload["id"]]

    documents: list[NotionPageDocument] = []
    for data_source_id in data_source_ids:
        row_pages = query_data_source_pages(data_source_id)
        for row_page in row_pages:
            documents.append(build_page_document(row_page, include_blocks=True))

    return documents


def fetch_notion_documents(target_id: str) -> list[NotionPageDocument]:
    try:
        return fetch_notion_page_documents(target_id)
    except requests.HTTPError as exc:
        if exc.response is None or exc.response.status_code != 404:
            raise

    try:
        return fetch_notion_database_documents(target_id)
    except requests.HTTPError as exc:
        if exc.response is not None and exc.response.status_code == 404:
            raise ValueError(
                "Notion object was not found through page, database, or data source APIs. "
                "Check the ID, workspace, and connection access."
            ) from exc
        raise
