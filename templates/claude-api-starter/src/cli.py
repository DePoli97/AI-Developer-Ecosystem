"""
Command-line entry point. Usage:

    python -m src.cli "your question here"
    python -m src.cli --stream "your question here"
"""

from __future__ import annotations

import argparse
import sys

from .client import ClaudeClient
from .config import load_config


def main() -> int:
    parser = argparse.ArgumentParser(description="Talk to Claude from the command line.")
    parser.add_argument("question", nargs="+", help="The question to ask.")
    parser.add_argument("--stream", action="store_true", help="Stream tokens to stdout.")
    args = parser.parse_args()

    cfg = load_config()
    client = ClaudeClient(cfg)
    messages = [{"role": "user", "content": " ".join(args.question)}]

    if args.stream:
        client.stream(messages, on_token=lambda t: sys.stdout.write(t) or sys.stdout.flush())
        print()
    else:
        print(client.complete(messages))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
