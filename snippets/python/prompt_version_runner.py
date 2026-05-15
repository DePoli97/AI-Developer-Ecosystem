"""
prompt_version_runner.py

Lightweight golden-example test harness for versioned LLM prompts.

Problem: prompt changes are silent - no exceptions, just subtly wrong outputs.
Solution: version prompt files + maintain a golden_examples.json that defines
         what correct looks like for each prompt, and run it before every deploy.

Usage:
    python prompt_version_runner.py --self-test
    python prompt_version_runner.py --prompts-dir prompts/ --golden prompts/golden_examples.json
    python prompt_version_runner.py --model claude-haiku-4-5-20251001

Exit code: 0 if all cases pass, 1 if any case fails (CI-friendly).

Dependencies: anthropic>=0.28
    pip install anthropic

Environment:
    ANTHROPIC_API_KEY  required

golden_examples.json schema
---------------------------
[
  {
    "prompt_file": "summarizer_v2.txt",
    "cases": [
      {
        "id": "human-readable-id",
        "input": { "text": "..." },
        "expected": {
          "max_sentences": 3,
          "must_contain_any": ["foo", "bar"],
          "must_not_contain": ["Sure", "Here"],
          "exact_match": "verbatim string"
        }
      }
    ]
  }
]
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import textwrap
from pathlib import Path
from typing import Any

import anthropic

DEFAULT_PROMPTS_DIR = "prompts"
DEFAULT_GOLDEN_FILE = "prompts/golden_examples.json"
DEFAULT_MODEL = "claude-haiku-4-5-20251001"
MAX_TOKENS = 512

client = anthropic.Anthropic()


def load_prompt(prompts_dir: Path, filename: str) -> str:
    path = prompts_dir / filename
    if not path.exists():
        available = [p.name for p in prompts_dir.glob("*.txt")]
        raise FileNotFoundError(
            f"Prompt file not found: {path}\nAvailable: {available}"
        )
    return path.read_text(encoding="utf-8").strip()


def fill_template(template: str, variables: dict[str, str]) -> str:
    for key, value in variables.items():
        template = template.replace("{{" + key + "}}", str(value))
    return template


def call_model(system: str, user_message: str, model: str) -> str:
    response = client.messages.create(
        model=model,
        max_tokens=MAX_TOKENS,
        system=system,
        messages=[{"role": "user", "content": user_message}],
    )
    return response.content[0].text.strip()


def count_sentences(text: str) -> int:
    return len(re.findall(r"[.!?]+", text))


def evaluate(output: str, expected: dict[str, Any]) -> tuple[bool, list[str]]:
    """Check output against expected spec. All keys optional and composable."""
    failures: list[str] = []
    lower_out = output.lower()

    if "exact_match" in expected:
        want = expected["exact_match"].strip()
        if output != want:
            failures.append(
                f"exact_match failed.\n  Expected: {want!r}\n  Got:      {output!r}"
            )

    if "max_sentences" in expected:
        n = count_sentences(output)
        limit = expected["max_sentences"]
        if n > limit:
            failures.append(f"max_sentences: got {n}, limit is {limit}")

    if "must_contain_any" in expected:
        keywords = expected["must_contain_any"]
        if not any(kw.lower() in lower_out for kw in keywords):
            failures.append(f"must_contain_any: none of {keywords} found")

    if "must_not_contain" in expected:
        keywords = expected["must_not_contain"]
        hits = [kw for kw in keywords if kw.lower() in lower_out]
        if hits:
            failures.append(f"must_not_contain: found forbidden strings {hits}")

    return (len(failures) == 0), failures


def run_suite(
    prompts_dir: Path,
    golden_path: Path,
    model: str,
    verbose: bool = False,
) -> bool:
    suite: list[dict] = json.loads(golden_path.read_text(encoding="utf-8"))
    total, passed, failed = 0, 0, 0

    for prompt_spec in suite:
        prompt_file: str = prompt_spec["prompt_file"]
        cases: list[dict] = prompt_spec.get("cases", [])
        system_template = load_prompt(prompts_dir, prompt_file)

        sep = "=" * 60
        print(f"\n{sep}")
        print(f"Prompt : {prompt_file}   ({len(cases)} case(s))")
        print(f"Model  : {model}")
        print(sep)

        for case in cases:
            total += 1
            case_id: str = case.get("id", f"case-{total}")
            inputs: dict = case.get("input", {})
            system = fill_template(system_template, inputs)
            user_msg: str = inputs.get(
                "user_message",
                inputs.get("text", next(iter(inputs.values()), "")),
            )

            output = call_model(system, user_msg, model)
            ok, issues = evaluate(output, case.get("expected", {}))

            status = "PASS" if ok else "FAIL"
            print(f"\n  [{status}] {case_id}")

            if ok:
                passed += 1
                preview = output[:120] + ("..." if len(output) > 120 else "")
                print(f"        Output: {preview!r}")
            else:
                failed += 1
                for issue in issues:
                    print(textwrap.indent(issue, "        ! "))
                if verbose:
                    print(f"        Full output:\n{textwrap.indent(output, '          ')}")
                else:
                    print(f"        Output: {output[:200]!r}")

    print(f"\n{'=' * 60}")
    print(f"Results: {passed}/{total} passed, {failed} failed")
    print(f"{'=' * 60}\n")
    return failed == 0


def run_self_test() -> None:
    """Verify evaluator logic without API calls."""
    print("Running evaluator self-test (no API call)...\n")

    cases = [
        ("hello world",          {"exact_match": "hello world"},              True),
        ("hello world!",         {"exact_match": "hello world"},              False),
        ("One. And two.",        {"max_sentences": 3},                        True),
        ("One. Two. Three. Four.", {"max_sentences": 3},                      False),
        ("RAG is a retrieval technique.", {"must_contain_any": ["RAG"]},      True),
        ("Neural networks.",      {"must_contain_any": ["RAG"]},              False),
        ("The answer is 42.",     {"must_not_contain": ["Sure", "Certainly"]}, True),
        ("Sure, here it is.",     {"must_not_contain": ["Sure"]},             False),
        ("RAG combines retrieval and generation.", {
            "max_sentences": 2,
            "must_contain_any": ["RAG", "retrieval"],
            "must_not_contain": ["Sure"],
        }, True),
    ]

    errors = 0
    for i, (output, expected, should_pass) in enumerate(cases):
        ok, issues = evaluate(output, expected)
        match = ok == should_pass
        status = "OK  " if match else "BUG "
        label = "pass" if ok else "fail"
        print(f"  [{status}] case {i+1:02d}: evaluator={label}, expected={'pass' if should_pass else 'fail'}")
        if not match:
            errors += 1
            for issue in issues:
                print(textwrap.indent(issue, "        "))

    if errors:
        print(f"\nSelf-test FAILED: {errors} bug(s).\n")
        sys.exit(1)
    else:
        print(f"\nSelf-test passed ({len(cases)} cases).\n")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run golden-example regression tests against versioned LLM prompts."
    )
    parser.add_argument("--prompts-dir", default=DEFAULT_PROMPTS_DIR)
    parser.add_argument("--golden", default=DEFAULT_GOLDEN_FILE)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--self-test", action="store_true",
                        help="Run evaluator self-test without API calls, then exit")
    args = parser.parse_args()

    if args.self_test:
        run_self_test()
        return

    prompts_dir = Path(args.prompts_dir)
    golden_path = Path(args.golden)

    if not prompts_dir.exists():
        print(f"Error: prompts directory '{prompts_dir}' not found.", file=sys.stderr)
        sys.exit(1)
    if not golden_path.exists():
        print(f"Error: golden examples file '{golden_path}' not found.", file=sys.stderr)
        sys.exit(1)
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("Error: ANTHROPIC_API_KEY is not set.", file=sys.stderr)
        sys.exit(1)

    success = run_suite(prompts_dir, golden_path, args.model, args.verbose)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
