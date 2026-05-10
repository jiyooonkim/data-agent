from __future__ import annotations

import argparse
import logging

from db.seed_fake_data import seed_demo_data
from ingestion.notion_to_vector import ingest_notion_to_vector
from service.doc_qa_service import ask_doc
from service.qa_service import ask


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="data-agent CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    ask_parser = subparsers.add_parser("ask", help="Generate SQL and query PostgreSQL")
    ask_parser.add_argument("--question", required=True, help="Natural-language analytics question")

    ask_doc_parser = subparsers.add_parser("ask-doc", help="Answer document questions from Notion vector search")
    ask_doc_parser.add_argument("--question", required=True, help="Document or policy question")

    subparsers.add_parser("seed-demo-data", help="Insert demo data into PostgreSQL for Slack/CLI QA testing")
    subparsers.add_parser("ingest-notion", help="Read Notion pages and store chunks in pgvector")

    return parser


def main():
    logging.basicConfig(level=logging.INFO)
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "ask":
        result = ask(args.question)
        print("SQL:")
        print(result["sql"])
        print()
        print("RESULT:")
        print(result["answer_text"])
    elif args.command == "ask-doc":
        result = ask_doc(args.question)
        print("ANSWER:")
        print(result["answer_text"])
        print()
        print("CONTEXT:")
        for row in result["rows"]:
            print(f"- {row[1]} / chunk {row[2]} / similarity={row[4]:.4f}")
    elif args.command == "seed-demo-data":
        print(seed_demo_data())
    elif args.command == "ingest-notion":
        print(ingest_notion_to_vector())


if __name__ == "__main__":
    main()
