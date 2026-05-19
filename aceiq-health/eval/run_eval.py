"""Eval runner: POST each question to /api/v1/query and compute 6 metrics."""
from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from pathlib import Path
from typing import Any

import httpx

ROOT = Path(__file__).resolve().parent.parent
QUESTIONS_FILE = Path(__file__).parent / "questions.json"

DEFAULT_API_URL = "http://localhost:8000"


def run_eval(api_url: str = DEFAULT_API_URL, timeout: float = 30.0) -> int:
    questions = json.loads(QUESTIONS_FILE.read_text())

    print(f"\n{'='*66}")
    print(f" AceIQ Health — Eval Suite ({len(questions)} questions)")
    print(f" API: {api_url}")
    print(f"{'='*66}\n")

    results: list[dict[str, Any]] = []

    for q in questions:
        qid = q["id"]
        question = q["question"]
        print(f"  [{qid}] {question[:72]}…" if len(question) > 72 else f"  [{qid}] {question}")

        try:
            resp = httpx.post(
                f"{api_url}/api/v1/query",
                json={"question": question},
                timeout=timeout,
            )
            resp.raise_for_status()
            data = resp.json()
        except httpx.ConnectError:
            print(f"       ✗ Connection refused — is the API running at {api_url}?")
            sys.exit(1)
        except Exception as exc:
            print(f"       ✗ Request failed: {exc}")
            results.append(
                {
                    "id": qid,
                    "refused": False,
                    "answer": "",
                    "citations": [],
                    "verifier_score": None,
                    "latency_ms": 0,
                    "error": str(exc),
                }
            )
            continue

        results.append(
            {
                "id": qid,
                "refused": data.get("refused", False),
                "answer": data.get("answer", ""),
                "citations": data.get("citations", []),
                "verifier_score": data.get("verifier_score"),
                "latency_ms": data.get("latency_ms", 0),
            }
        )
        status = "REFUSED" if data.get("refused") else f"✓ ({data.get('latency_ms', 0)}ms)"
        print(f"       {status}")

    return _print_metrics(questions, results)


def _print_metrics(questions: list[dict], results: list[dict]) -> int:
    answer_qs = [q for q in questions if not q["should_refuse"]]
    refusal_qs = [q for q in questions if q["should_refuse"]]

    res_map = {r["id"]: r for r in results}

    # 1. Retrieval drug match
    drug_matches = 0
    for q in answer_qs:
        r = res_map.get(q["id"])
        if not r or r.get("refused"):
            continue
        expected = (q.get("expected_drug") or "").lower()
        if not expected:
            drug_matches += 1
            continue
        if any(
            expected in (c.get("drug_name") or "").lower()
            for c in r.get("citations", [])
        ):
            drug_matches += 1
    drug_match_pct = drug_matches / len(answer_qs) if answer_qs else 0.0

    # 2. Section match
    section_matches = 0
    for q in answer_qs:
        r = res_map.get(q["id"])
        if not r or r.get("refused"):
            continue
        expected_secs = q.get("expected_sections", [])
        if not expected_secs:
            section_matches += 1
            continue
        cited_secs = {c.get("section") for c in r.get("citations", [])}
        if any(sec in cited_secs for sec in expected_secs):
            section_matches += 1
    section_match_pct = section_matches / len(answer_qs) if answer_qs else 0.0

    # 3. Must-mention coverage
    coverages: list[float] = []
    for q in answer_qs:
        r = res_map.get(q["id"])
        if not r or r.get("refused"):
            coverages.append(0.0)
            continue
        terms = q.get("must_mention", [])
        if not terms:
            coverages.append(1.0)
            continue
        answer_lower = r.get("answer", "").lower()
        found = sum(1 for t in terms if t.lower() in answer_lower)
        coverages.append(found / len(terms))
    avg_coverage = statistics.mean(coverages) if coverages else 0.0

    # 4. Refusal correctness
    refusal_correct = sum(
        1
        for q in questions
        if res_map.get(q["id"], {}).get("refused", False) == q["should_refuse"]
    )
    refusal_pct = refusal_correct / len(questions) if questions else 0.0

    # 5. Avg verifier score
    v_scores = [
        r["verifier_score"]
        for r in results
        if not r.get("refused") and r.get("verifier_score") is not None
    ]
    avg_verifier = statistics.mean(v_scores) if v_scores else None

    # 6. Avg latency
    latencies = [r["latency_ms"] for r in results if "latency_ms" in r]
    avg_latency = statistics.mean(latencies) if latencies else 0.0

    # Targets from the brief
    TARGETS = {
        "drug_match": 0.90,
        "section_match": 0.80,
        "coverage": 0.75,
        "refusal": 1.00,
        "verifier": 0.75,
        "latency_ms": 3000,
    }

    def _pct(v: float) -> str:
        return f"{v * 100:.1f}%"

    def _pass(val: float, target: float, higher_is_better: bool = True) -> str:
        ok = val >= target if higher_is_better else val <= target
        return "✅ PASS" if ok else "❌ FAIL"

    print(f"\n{'='*66}")
    print(f"  METRICS RESULTS")
    print(f"{'='*66}")
    print(f"  {'Metric':<32} {'Result':>10}  {'Target':>8}  {'Status'}")
    print(f"  {'-'*60}")
    print(
        f"  {'Retrieval drug match':<32} {_pct(drug_match_pct):>10}  "
        f"{'≥90%':>8}  {_pass(drug_match_pct, TARGETS['drug_match'])}"
    )
    print(
        f"  {'Section match':<32} {_pct(section_match_pct):>10}  "
        f"{'≥80%':>8}  {_pass(section_match_pct, TARGETS['section_match'])}"
    )
    print(
        f"  {'Must-mention coverage':<32} {_pct(avg_coverage):>10}  "
        f"{'≥75%':>8}  {_pass(avg_coverage, TARGETS['coverage'])}"
    )
    print(
        f"  {'Refusal correctness':<32} {_pct(refusal_pct):>10}  "
        f"{'100%':>8}  {_pass(refusal_pct, TARGETS['refusal'])}"
    )
    verifier_str = f"{avg_verifier:.3f}" if avg_verifier is not None else "    N/A"
    verifier_status = (
        _pass(avg_verifier, TARGETS["verifier"])
        if avg_verifier is not None
        else "⚠️  N/A (no LLM)"
    )
    print(
        f"  {'Avg verifier score':<32} {verifier_str:>10}  "
        f"{'≥0.75':>8}  {verifier_status}"
    )
    print(
        f"  {'Avg latency (ms)':<32} {avg_latency:>10.0f}  "
        f"{'≤3000':>8}  {_pass(avg_latency, TARGETS['latency_ms'], higher_is_better=False)}"
    )
    print(f"{'='*66}\n")

    all_pass = (
        drug_match_pct >= TARGETS["drug_match"]
        and section_match_pct >= TARGETS["section_match"]
        and avg_coverage >= TARGETS["coverage"]
        and refusal_pct >= TARGETS["refusal"]
        and avg_latency <= TARGETS["latency_ms"]
    )
    if all_pass:
        print("  🎉 All hard targets met — v1 acceptance criteria PASSED\n")
        return 0
    else:
        print("  ⚠️  One or more targets not met — see failures above\n")
        return 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AceIQ Health eval suite")
    parser.add_argument("--api-url", default=DEFAULT_API_URL)
    parser.add_argument("--timeout", type=float, default=30.0)
    args = parser.parse_args()
    sys.exit(run_eval(api_url=args.api_url, timeout=args.timeout))
