from __future__ import annotations

import argparse
import logging

from db.seed_fake_data import seed_demo_data
from service.qa_service import ask


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="data-agent CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    ask_parser = subparsers.add_parser("ask", help="Generate SQL and query PostgreSQL")
    ask_parser.add_argument("--question", required=True, help="Natural-language analytics question")

    subparsers.add_parser("seed-demo-data", help="Insert demo data into PostgreSQL for Slack/CLI QA testing")

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
    elif args.command == "seed-demo-data":
        print(seed_demo_data())


if __name__ == "__main__":
    main()
