"""Build the profile README — replaces marker sections with live GitHub data.

Pulls from the GitHub GraphQL API in a single request:
    - Recent releases across all public, non-fork repos
    - Most recently pushed public repos (excluding the profile repo itself)

Replaces content between HTML comment markers in README.md:
    <!-- recent_releases starts --> ... <!-- recent_releases ends -->
    <!-- recent_activity starts --> ... <!-- recent_activity ends -->

Run via the GitHub Action in .github/workflows/build.yml on a daily cron.

Requires the GITHUB_TOKEN environment variable to be set. The workflow injects
the default repository token automatically — no PAT needed for public data.
"""

from __future__ import annotations

import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests

USER = "Abdulrahman-Elsmmany"
PROFILE_REPO = USER  # the special repo with the same name as the user
README = Path(__file__).parent / "README.md"
TOKEN = os.environ.get("GITHUB_TOKEN")
HEADERS = {
    "Authorization": f"Bearer {TOKEN}" if TOKEN else "",
    "Accept": "application/vnd.github+json",
    "User-Agent": f"{USER}-profile-builder",
}

GRAPHQL_QUERY = """
query($login: String!) {
  user(login: $login) {
    repositories(
      first: 50,
      orderBy: {field: PUSHED_AT, direction: DESC},
      ownerAffiliations: OWNER,
      privacy: PUBLIC,
      isFork: false
    ) {
      nodes {
        name
        url
        pushedAt
        description
        primaryLanguage { name color }
        stargazerCount
        isArchived
        releases(first: 3, orderBy: {field: CREATED_AT, direction: DESC}) {
          nodes {
            tagName
            name
            url
            publishedAt
            isPrerelease
            isDraft
          }
        }
        defaultBranchRef {
          target {
            ... on Commit {
              history(first: 1) {
                nodes {
                  messageHeadline
                  url
                  committedDate
                }
              }
            }
          }
        }
      }
    }
  }
}
"""


def fetch_data() -> list[dict]:
    """Fetch repo + release data from the GitHub GraphQL API."""
    response = requests.post(
        "https://api.github.com/graphql",
        json={"query": GRAPHQL_QUERY, "variables": {"login": USER}},
        headers=HEADERS,
        timeout=30,
    )
    response.raise_for_status()
    payload = response.json()
    if "errors" in payload:
        sys.exit(f"GraphQL errors: {payload['errors']}")
    return payload["data"]["user"]["repositories"]["nodes"]


def format_relative(iso_ts: str) -> str:
    """Turn an ISO 8601 timestamp into a short relative date."""
    when = datetime.fromisoformat(iso_ts.replace("Z", "+00:00"))
    delta = datetime.now(timezone.utc) - when
    days = delta.days
    if days < 0:
        return when.strftime("%Y-%m-%d")
    if days == 0:
        hours = delta.seconds // 3600
        if hours == 0:
            return "just now"
        return f"{hours}h ago"
    if days == 1:
        return "yesterday"
    if days < 7:
        return f"{days}d ago"
    if days < 30:
        weeks = days // 7
        return f"{weeks}w ago"
    if days < 365:
        months = days // 30
        return f"{months}mo ago"
    years = days // 365
    return f"{years}y ago"


def build_releases(repos: list[dict], limit: int = 5) -> str:
    """Build the bulleted list of recent releases across all repos."""
    releases = []
    for repo in repos:
        if repo.get("isArchived"):
            continue
        for rel in repo["releases"]["nodes"]:
            if rel["isPrerelease"] or rel["isDraft"]:
                continue
            releases.append(
                {
                    "repo": repo["name"],
                    "tag": rel["tagName"],
                    "url": rel["url"],
                    "date": rel["publishedAt"],
                }
            )
    releases.sort(key=lambda r: r["date"], reverse=True)
    if not releases:
        return (
            "- _No tagged releases yet — see the activity feed for what's "
            "shipping right now._"
        )
    lines = [
        f"- [**{r['repo']}** {r['tag']}]({r['url']}) — {format_relative(r['date'])}"
        for r in releases[:limit]
    ]
    return "\n".join(lines)


def build_activity(repos: list[dict], limit: int = 5) -> str:
    """Build the bulleted list of recently active repos."""
    activity = []
    for repo in repos:
        if repo["name"] == PROFILE_REPO or repo.get("isArchived"):
            continue
        ref = repo.get("defaultBranchRef")
        if not ref or not ref.get("target"):
            continue
        history = ref["target"].get("history", {}).get("nodes", [])
        if not history:
            continue
        commit = history[0]
        activity.append(
            {
                "name": repo["name"],
                "url": repo["url"],
                "stars": repo["stargazerCount"],
                "lang": (repo.get("primaryLanguage") or {}).get("name"),
                "date": commit["committedDate"],
            }
        )
    if not activity:
        return "- _No recent public activity._"
    activity.sort(key=lambda r: r["date"], reverse=True)
    lines = []
    for r in activity[:limit]:
        meta_parts = []
        if r["lang"]:
            meta_parts.append(f"`{r['lang']}`")
        if r["stars"] > 0:
            meta_parts.append(f"⭐ {r['stars']}")
        meta = " · ".join(meta_parts)
        meta_str = f" — {meta}" if meta else ""
        lines.append(
            f"- [**{r['name']}**]({r['url']}){meta_str} · "
            f"{format_relative(r['date'])}"
        )
    return "\n".join(lines)


def replace_chunk(content: str, marker: str, chunk: str) -> str:
    """Replace content between <!-- marker starts --> ... <!-- marker ends -->."""
    pattern = rf"(<!-- {marker} starts -->).*?(<!-- {marker} ends -->)"
    replacement = rf"\1\n{chunk}\n\2"
    new_content, n = re.subn(pattern, replacement, content, flags=re.DOTALL)
    if n == 0:
        print(f"WARNING: marker '{marker}' not found in README.md — skipping.")
        return content
    return new_content


def main() -> None:
    if not TOKEN:
        sys.exit("ERROR: GITHUB_TOKEN environment variable is required.")

    print(f"Fetching data for user: {USER}")
    repos = fetch_data()
    print(f"Found {len(repos)} public, non-fork repositories.")

    releases_chunk = build_releases(repos)
    activity_chunk = build_activity(repos)

    print("\n--- Recent releases ---")
    print(releases_chunk)
    print("\n--- Recent activity ---")
    print(activity_chunk)

    text = README.read_text(encoding="utf-8")
    text = replace_chunk(text, "recent_releases", releases_chunk)
    text = replace_chunk(text, "recent_activity", activity_chunk)
    README.write_text(text, encoding="utf-8")
    print("\nREADME.md updated.")


if __name__ == "__main__":
    main()
