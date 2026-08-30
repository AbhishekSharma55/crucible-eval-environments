"""Fetch immutable candidate inputs from GitHub GraphQL into the disk cache."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import random
import time
import urllib.error
import urllib.request


ROOT = Path(__file__).resolve().parents[1]
ENDPOINT = "https://api.github.com/graphql"
PR_QUERY = """
query CandidatePullRequests($owner: String!, $name: String!, $cursor: String) {
  repository(owner: $owner, name: $name) {
    pullRequests(first: 100, after: $cursor, states: MERGED, orderBy: {field: UPDATED_AT, direction: DESC}) {
      pageInfo { hasNextPage endCursor }
      nodes {
        number title body mergedAt url
        mergeCommit { oid parents(first: 2) { nodes { oid } } }
        closingIssuesReferences(first: 20) { nodes { number body url } }
        files(first: 100) {
          pageInfo { hasNextPage endCursor }
          totalCount
          nodes { path }
        }
      }
    }
  }
  rateLimit { remaining resetAt cost }
}
"""

FILES_QUERY = """
query PullRequestFiles($owner: String!, $name: String!, $number: Int!, $cursor: String) {
  repository(owner: $owner, name: $name) {
    pullRequest(number: $number) {
      files(first: 100, after: $cursor) {
        pageInfo { hasNextPage endCursor }
        totalCount
        nodes { path }
      }
    }
  }
  rateLimit { remaining resetAt cost }
}
"""

MAX_CHANGED_FILES = 300


def request_graphql(
    token: str,
    query: str,
    variables: dict[str, object],
    attempts: int = 6,
) -> dict[str, object]:
    payload = json.dumps({"query": query, "variables": variables}).encode()
    for attempt in range(attempts):
        request = urllib.request.Request(
            ENDPOINT,
            data=payload,
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json", "User-Agent": "crucible-phase1"},
        )
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                result = json.load(response)
            if result.get("errors"):
                raise RuntimeError(json.dumps(result["errors"], sort_keys=True))
            return result
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as exc:
            if attempt == attempts - 1:
                raise RuntimeError(f"GitHub request failed after {attempts} attempts: {exc}") from exc
            time.sleep(min(60, 2**attempt) + random.Random(attempt).random())
    raise AssertionError("unreachable")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pages", type=int, default=5, help="100 merged PRs per page")
    parser.add_argument("--repo", action="append", help="limit fetch to owner/name (repeatable)")
    args = parser.parse_args()
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        raise SystemExit("GITHUB_TOKEN is required for cache refresh")
    config = json.loads((ROOT / "config/repos.json").read_text(encoding="utf-8"))
    wanted = set(args.repo or [])
    for item in config["repos"]:
        repo = item["repo"]
        if item["status"] != "accepted" or (wanted and repo not in wanted):
            continue
        owner, name = repo.split("/", 1)
        output = ROOT / "data/github-api" / repo.replace("/", "--")
        output.mkdir(parents=True, exist_ok=True)
        cursor = None
        for page in range(1, args.pages + 1):
            result = request_graphql(token, PR_QUERY, {"owner": owner, "name": name, "cursor": cursor})
            target = output / f"merged-prs-{page:03d}.json"
            target.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            connection = result["data"]["repository"]["pullRequests"]
            print(f"cached {repo:<32} page={page} prs={len(connection['nodes'])}")
            for pr in connection["nodes"]:
                files = pr["files"]
                for stale in output.glob(f"pr-{pr['number']}-files-*.json"):
                    stale.unlink()
                if files["totalCount"] <= len(files["nodes"]) or files["totalCount"] > MAX_CHANGED_FILES:
                    continue
                files_cursor = files["pageInfo"]["endCursor"]
                files_page = 1
                while files["pageInfo"]["hasNextPage"] and files_page * 100 < files["totalCount"]:
                    files_page += 1
                    supplemental = request_graphql(
                        token,
                        FILES_QUERY,
                        {"owner": owner, "name": name, "number": pr["number"], "cursor": files_cursor},
                    )
                    file_connection = supplemental["data"]["repository"]["pullRequest"]["files"]
                    file_target = output / f"pr-{pr['number']}-files-{files_page:03d}.json"
                    file_target.write_text(json.dumps(supplemental, indent=2, sort_keys=True) + "\n", encoding="utf-8")
                    if not file_connection["pageInfo"]["hasNextPage"]:
                        break
                    files_cursor = file_connection["pageInfo"]["endCursor"]
            if not connection["pageInfo"]["hasNextPage"]:
                break
            cursor = connection["pageInfo"]["endCursor"]
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
