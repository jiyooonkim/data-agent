import argparse

from ingestion.sheet_to_postgres import run as run_sheet_to_postgres
from service.qa_service import answer_question


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["ingest", "ask"])
    parser.add_argument("--question")
    args = parser.parse_args()

    if args.command == "ingest":
        run_sheet_to_postgres()
        return

    if not args.question:
        raise SystemExit("--question is required when command is ask.")

    print(answer_question(args.question))


if __name__ == "__main__":
    main()
