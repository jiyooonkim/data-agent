import unittest
from unittest.mock import patch

from ingestion.notion_client import collect_child_page_ids, fetch_notion_documents


class NotionClientTest(unittest.TestCase):
    def test_collect_child_page_ids_recurses_nested_blocks(self):
        blocks = [
            {
                "id": "parent-toggle",
                "type": "toggle",
                "has_children": True,
            },
            {
                "id": "child-page-1",
                "type": "child_page",
                "has_children": False,
                "child_page": {"title": "Child 1"},
            },
        ]

        nested_blocks = [
            {
                "id": "child-page-2",
                "type": "child_page",
                "has_children": False,
                "child_page": {"title": "Child 2"},
            }
        ]

        with patch("ingestion.notion_client.list_block_children", return_value=nested_blocks):
            self.assertEqual(
                collect_child_page_ids(blocks),
                ["child-page-2", "child-page-1"],
            )

    def test_fetch_notion_documents_recursively_loads_child_pages_once(self):
        page_payloads = {
            "root-page": {
                "id": "root-page",
                "url": "https://example.com/root",
                "last_edited_time": "2026-05-17T00:00:00.000Z",
                "properties": {"title": {"type": "title", "title": [{"plain_text": "Root"}]}},
            },
            "child-page": {
                "id": "child-page",
                "url": "https://example.com/child",
                "last_edited_time": "2026-05-17T00:00:00.000Z",
                "properties": {"title": {"type": "title", "title": [{"plain_text": "Child"}]}},
            },
        }

        block_children = {
            "root-page": [
                {
                    "id": "child-page",
                    "type": "child_page",
                    "has_children": False,
                    "child_page": {"title": "Child"},
                }
            ],
            "child-page": [
                {
                    "id": "root-page",
                    "type": "child_page",
                    "has_children": False,
                    "child_page": {"title": "Root"},
                }
            ],
        }

        def notion_get_side_effect(path: str, params=None):
            del params
            if path.startswith("/pages/"):
                return page_payloads[path.rsplit("/", 1)[-1]]
            raise AssertionError(f"Unexpected path: {path}")

        def list_block_children_side_effect(block_id: str):
            return block_children.get(block_id, [])

        with patch("ingestion.notion_client.notion_get", side_effect=notion_get_side_effect), patch(
            "ingestion.notion_client.list_block_children",
            side_effect=list_block_children_side_effect,
        ):
            documents = fetch_notion_documents("root-page")

        self.assertEqual([document.page_id for document in documents], ["root-page", "child-page"])


if __name__ == "__main__":
    unittest.main()
