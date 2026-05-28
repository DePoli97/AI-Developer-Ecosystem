"""
eval_judge_llm.py
-----------------
LLM-as-judge: score model outputs against a rubric using Claude.

Pattern
-------
For each (input, candidate_output) pair, send a structured judgment
prompt to a "judge" model and extract a numeric score + rationale.
Useful for:
  - automated regression testing of prompts
  - A/B comparison of two model outputs
  - grading open-ended answers where exact-match fails

Usage
-----
    from eval_judge_llm import judge, batch_judge

    score, rationale = judge(
        question="What is the capital of France?",
        answer="Paris is the capital city of France.",
        rubric="Award 1 point if the answer is factually correct and concise.",
    )
    # score: 1.0, rationale: "..."

    results = batch_judge(pairs, rubric="...")

Requirements
------------
    pip install anthropic
"""

from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass
from typing import Sequence

import anthropic

# ---------------------------------------------------------------------------
# Default judge model — use a smaller / cheaper model for bulk evals
# ---------------------------------------------------------------------------
JUDGE_MODEL = "claude-haiku-4-5-20251001"

JUDGE_SYSTEM = """You are an objective evaluation judge. You will be given:
- A QUESTION or task description
- A CANDIDATE ANSWER to evaluate
- A RUBRIC describing what makes a good answer

Respond with a JSON object only — no prose outside the JSON.
Format:
{
  "score": <float between 0.0 and 1.0>,
  "rationale": "<one or two sentences explaining the score>"
}"""

JUDGE_PROMPT_TEMPLATE = """QUESTION:
{question}

CANDIDATE ANSWER:
{answer}

RUBRIC:
{rubric}"""


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------

@dataclass
class JudgmentResult:
    question: str
    answer: str
    score: float
    rationale: str
    raw_response: str = ""


# ---------------------------------------------------------------------------
# Core judge call
# ---------------------------------------------------------------------------

def judge(
    question: str,
    answer: str,
    rubric: str,
    model: str = JUDGE_MODEL,
    max_tokens: int = 256,
    retries: int = 3,
) -> tuple[float, str]:
    """
    Score a single (question, answer) pair against a rubric.

    Returns
    -------
    (score, rationale) where score is in [0.0, 1.0].
    """
    client = anthropic.Anthropic()
    prompt = JUDGE_PROMPT_TEMPLATE.format(
        question=question, answer=answer, rubric=rubric
    )

    for attempt in range(retries):
        try:
            response = client.messages.create(
                model=model,
                max_tokens=max_tokens,
                system=JUDGE_SYSTEM,
                messages=[{"role": "user", "content": prompt}],
            )
            text = response.content[0].text.strip()
            data = _parse_json_response(text)
            score = float(data["score"])
            rationale = str(data.get("rationale", ""))
            return score, rationale
        except (anthropic.RateLimitError, anthropic.APIStatusError) as e:
            if attempt < retries - 1:
                time.sleep(2 ** attempt)
            else:
                raise
        except (KeyError, ValueError, json.JSONDecodeError) as e:
            if attempt < retries - 1:
                continue
            raise ValueError(f"Judge returned unparseable response: {text!r}") from e

    raise RuntimeError("Unreachable")


def _parse_json_response(text: str) -> dict:
    """Extract JSON from response, handling markdown code fences."""
    # strip ```json ... ``` fences if present
    match = re.search(r"```(?:json)?\s*([\s\S]+?)```", text)
    if match:
        text = match.group(1)
    return json.loads(text)


# ---------------------------------------------------------------------------
# Batch judge
# ---------------------------------------------------------------------------

@dataclass
class EvalPair:
    question: str
    answer: str


def batch_judge(
    pairs: Sequence[EvalPair],
    rubric: str,
    model: str = JUDGE_MODEL,
    delay_between: float = 0.2,
) -> list[JudgmentResult]:
    """
    Judge a list of (question, answer) pairs.

    Parameters
    ----------
    pairs           : sequence of EvalPair
    rubric          : shared rubric applied to every pair
    model           : judge model
    delay_between   : seconds to sleep between API calls (rate limiting)

    Returns
    -------
    List of JudgmentResult sorted in the same order as `pairs`.
    """
    results = []
    for pair in pairs:
        score, rationale = judge(
            question=pair.question,
            answer=pair.answer,
            rubric=rubric,
            model=model,
        )
        results.append(
            JudgmentResult(
                question=pair.question,
                answer=pair.answer,
                score=score,
                rationale=rationale,
            )
        )
        time.sleep(delay_between)
    return results


def summarise(results: list[JudgmentResult]) -> dict:
    """Return aggregate stats for a batch of judgments."""
    if not results:
        return {"count": 0}
    scores = [r.score for r in results]
    return {
        "count": len(scores),
        "mean_score": round(sum(scores) / len(scores), 4),
        "min_score": min(scores),
        "max_score": max(scores),
        "pass_rate": round(sum(s >= 0.7 for s in scores) / len(scores), 4),
    }


# ---------------------------------------------------------------------------
# CLI demo
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    rubric = (
        "Award 1.0 if the answer is factually correct and directly addresses "
        "the question. Award 0.5 if partially correct or too verbose. "
        "Award 0.0 if wrong or irrelevant."
    )

    demo_pairs = [
        EvalPair("What is 2 + 2?", "4"),
        EvalPair("What is the capital of Japan?", "The capital of Japan is Tokyo."),
        EvalPair("Who wrote Hamlet?", "Beethoven wrote Hamlet."),
    ]

    print("Running LLM-as-judge demo...\n")
    results = batch_judge(demo_pairs, rubric=rubric)

    for r in results:
        print(f"Q: {r.question}")
        print(f"A: {r.answer}")
        print(f"Score: {r.score}  |  {r.rationale}\n")

    print("Summary:", summarise(results))
