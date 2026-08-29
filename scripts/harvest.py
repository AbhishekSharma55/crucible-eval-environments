"""Rebuild accepted and rejected candidates deterministically from API cache."""

from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import re
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
TEST_PATH = re.compile(r"(^|/)(tests?|testing)(/|$)|(^|/)(test_[^/]+|[^/]+_test)\.py$")
SOURCE_PATH = re.compile(r"\.py$")
SOURCE_EXCLUDED = re.compile(r"(^|/)(tests?|testing|docs?|examples?|benchmarks?)(/|$)")


def static_reason(candidate: dict[str, Any]) -> tuple[str | None, str | None]:
    if not candidate["linked_issues"]:
        return "no_linked_issue", None
    if not candidate["test_files"]:
        return "no_test_files_touched", None
    if not candidate["source_files"]:
        return "no_source_files_touched", None
    if candidate["files_truncated"]:
        return "other", "PR changes more than 100 files; cached file list is incomplete"
    if not candidate["parent_sha"]:
        return "other", "merge commit has no cached first parent"
    return None, None


def cached_prs(repo: str) -> list[dict[str, Any]]:
    directory = ROOT / "data/github-api" / repo.replace("/", "--")
    pages = sorted(directory.glob("merged-prs-*.json"))
    if not pages:
        raise RuntimeError(f"missing API cache for {repo}; online refresh is a separate explicit step")
    nodes: list[dict[str, Any]] = []
    for page in pages:
        payload = json.loads(page.read_text(encoding="utf-8"))
        nodes.extend(payload["data"]["repository"]["pullRequests"]["nodes"])
    return nodes


def build_candidate(repo: str, pr: dict[str, Any]) -> dict[str, Any]:
    files = sorted(node["path"] for node in pr["files"]["nodes"])
    test_files = [path for path in files if TEST_PATH.search(path)]
    source_files = [path for path in files if SOURCE_PATH.search(path) and not TEST_PATH.search(path) and not SOURCE_EXCLUDED.search(path)]
    merge = pr.get("mergeCommit") or {}
    parents = ((merge.get("parents") or {}).get("nodes") or [])
    issues = sorted(
        ({"number": issue["number"], "body": issue.get("body") or "", "url": issue.get("url")} for issue in pr["closingIssuesReferences"]["nodes"]),
        key=lambda value: value["number"],
    )
    candidate = {
        "repo": repo,
        "pr_number": pr["number"],
        "title": pr["title"],
        "body": pr.get("body") or "",
        "url": pr.get("url"),
        "merged_at": pr["mergedAt"],
        "merge_commit_sha": merge.get("oid"),
        "parent_sha": parents[0]["oid"] if parents else None,
        "linked_issues": issues,
        "issue_body_text": "\n\n".join(issue["body"] for issue in issues),
        "files_changed": files,
        "test_files": test_files,
        "source_files": source_files,
        "non_test_files": [path for path in files if path not in test_files],
        "files_truncated": pr["files"]["totalCount"] > len(files),
    }
    reason, note = static_reason(candidate)
    validation_path = ROOT / "data/validation" / repo.replace("/", "--") / f"pr-{pr['number']}.json"
    if reason is None:
        if validation_path.exists():
            validation = json.loads(validation_path.read_text(encoding="utf-8"))
            reason = validation.get("rejection_reason")
            note = validation.get("note")
            candidate["validation"] = validation
        else:
            reason, note = "other", "dynamic validation result is not cached"
    candidate["status"] = "accepted" if reason is None else "rejected"
    candidate["rejection_reason"] = reason
    candidate["rejection_note"] = note
    return candidate


def write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    content = "".join(json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n" for record in records)
    path.write_text(content, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "data/candidates")
    args = parser.parse_args()
    corpus = json.loads((ROOT / "config/repos.json").read_text(encoding="utf-8"))
    split = json.loads((ROOT / "config/split.json").read_text(encoding="utf-8"))
    active = [item for item in corpus["repos"] if item["status"] == "accepted"]
    assignment = split["assignment"]
    active_names = {item["repo"] for item in active}
    if set(assignment) != active_names:
        raise RuntimeError("config/split.json must assign every accepted repo exactly once")
    for bucket in ("dev", "heldout"):
        directory = args.output / bucket
        directory.mkdir(parents=True, exist_ok=True)
        for existing in directory.glob("*.jsonl"):
            existing.unlink()

    all_candidates: list[dict[str, Any]] = []
    for item in active:
        repo = item["repo"]
        candidates = sorted((build_candidate(repo, pr) for pr in cached_prs(repo)), key=lambda value: value["pr_number"])
        write_jsonl(args.output / assignment[repo] / f"{repo.replace('/', '--')}.jsonl", candidates)
        all_candidates.extend(candidates)

    histogram = Counter(candidate["rejection_reason"] for candidate in all_candidates if candidate["status"] == "rejected")
    dropped = [
        {"repo": item["repo"], "reason": item.get("drop_reason", "not accepted after probe")}
        for item in corpus["repos"]
        if item["status"] == "dropped"
    ]
    summary = {
        "schema_version": 1,
        "repos_attempted": len(corpus["repos"]),
        "repos_accepted": len(active),
        "accepted_repos": sorted(active_names),
        "repos_dropped": dropped,
        "total_candidates": len(all_candidates),
        "accepted_candidates": sum(candidate["status"] == "accepted" for candidate in all_candidates),
        "rejected_candidates": sum(candidate["status"] == "rejected" for candidate in all_candidates),
        "rejection_reason_histogram": dict(sorted(histogram.items())),
        "split_seed": split["seed"],
        "dev_repos": sorted(repo for repo, bucket in assignment.items() if bucket == "dev"),
        "heldout_repo_count": sum(bucket == "heldout" for bucket in assignment.values()),
    }
    (args.output / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, sort_keys=True))
    if len(all_candidates) < 300:
        raise RuntimeError(f"only {len(all_candidates)} candidates; at least 300 required")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
