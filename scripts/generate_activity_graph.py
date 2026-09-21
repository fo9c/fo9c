#!/usr/bin/env python3
"""Generate a self-hosted GitHub activity graph as a static SVG."""

from __future__ import annotations

import argparse
import html
import json
import os
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path


API_URL = "https://api.github.com/graphql"
QUERY = """
query ActivityGraph($login: String!) {
  user(login: $login) {
    contributionsCollection {
      contributionCalendar {
        totalContributions
        weeks {
          contributionDays {
            contributionCount
            date
          }
        }
      }
    }
  }
}
"""


@dataclass(frozen=True)
class Contribution:
    day: date
    count: int


def fetch_contributions(username: str, token: str, attempts: int = 5) -> dict:
    payload = json.dumps(
        {"query": QUERY, "variables": {"login": username}}
    ).encode("utf-8")
    request = urllib.request.Request(
        API_URL,
        data=payload,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "fo9c-profile-activity-graph",
            "X-GitHub-Api-Version": "2022-11-28",
        },
        method="POST",
    )

    last_error: Exception | None = None
    for attempt in range(attempts):
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                data = json.load(response)
            if data.get("errors"):
                raise RuntimeError(f"GitHub GraphQL error: {data['errors']}")
            return data
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as exc:
            last_error = exc
            retryable = not isinstance(exc, urllib.error.HTTPError) or exc.code in {
                403,
                429,
                500,
                502,
                503,
                504,
            }
            if not retryable or attempt == attempts - 1:
                break
            delay = min(2**attempt, 16)
            print(f"GitHub request failed; retrying in {delay}s: {exc}", file=sys.stderr)
            time.sleep(delay)

    raise RuntimeError(f"Unable to read GitHub contributions: {last_error}")


def parse_contributions(payload: dict, days: int) -> tuple[list[Contribution], int]:
    try:
        calendar = payload["data"]["user"]["contributionsCollection"][
            "contributionCalendar"
        ]
        raw_days = [
            item
            for week in calendar["weeks"]
            for item in week["contributionDays"]
        ]
    except (KeyError, TypeError) as exc:
        raise ValueError("Unexpected GitHub contribution response") from exc

    parsed = sorted(
        (
            Contribution(
                day=datetime.strptime(item["date"], "%Y-%m-%d").date(),
                count=max(0, int(item["contributionCount"])),
            )
            for item in raw_days
        ),
        key=lambda item: item.day,
    )
    if not parsed:
        raise ValueError("GitHub returned an empty contribution calendar")
    visible = parsed[-days:]
    return visible, sum(item.count for item in visible)


def smooth_path(points: list[tuple[float, float]]) -> str:
    if not points:
        return ""
    commands = [f"M {points[0][0]:.2f} {points[0][1]:.2f}"]
    for previous, current in zip(points, points[1:]):
        midpoint = (previous[0] + current[0]) / 2
        commands.append(
            f"C {midpoint:.2f} {previous[1]:.2f}, "
            f"{midpoint:.2f} {current[1]:.2f}, "
            f"{current[0]:.2f} {current[1]:.2f}"
        )
    return " ".join(commands)


def render_svg(username: str, contributions: list[Contribution], total: int) -> str:
    width, height = 900, 250
    left, right, top, bottom = 46, 882, 24, 190
    maximum = max((item.count for item in contributions), default=0)
    scale_max = max(4, maximum)
    x_step = (right - left) / max(1, len(contributions) - 1)
    points = [
        (
            left + index * x_step,
            bottom - (item.count / scale_max) * (bottom - top),
        )
        for index, item in enumerate(contributions)
    ]
    line_path = smooth_path(points)
    area_path = f"{line_path} L {points[-1][0]:.2f} {bottom} L {points[0][0]:.2f} {bottom} Z"

    labels = []
    for index, item in enumerate(contributions):
        if index % 5 == 0 or index == len(contributions) - 1:
            labels.append(
                f'<text class="axis" x="{points[index][0]:.2f}" y="222" '
                f'text-anchor="middle">{html.escape(item.day.strftime("%b %d"))}</text>'
            )

    dots = "".join(
        f'<circle cx="{x:.2f}" cy="{y:.2f}" r="3.3"><title>'
        f'{html.escape(item.day.isoformat())}: {item.count} contributions'
        f'</title></circle>'
        for (x, y), item in zip(points, contributions)
    )
    accessible_title = html.escape(
        f"{username} GitHub activity: {total} contributions in the last {len(contributions)} days"
    )

    return f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">
  <title id="title">{accessible_title}</title>
  <desc id="desc">A self-hosted line and area chart generated from GitHub contribution data.</desc>
  <defs>
    <linearGradient id="activity-fill" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="#40c463" stop-opacity="0.42"/>
      <stop offset="100%" stop-color="#40c463" stop-opacity="0.03"/>
    </linearGradient>
  </defs>
  <style>
    .axis {{ fill: #8b949e; font: 12px -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }}
    .baseline {{ stroke: #8b949e; stroke-opacity: .22; stroke-width: 1; }}
    .area {{ fill: url(#activity-fill); }}
    .line {{ fill: none; stroke: #3cb371; stroke-width: 3; stroke-linecap: round; stroke-linejoin: round; }}
    circle {{ fill: #3cb371; stroke: #ffffff; stroke-width: 1.5; }}
    @media (prefers-color-scheme: dark) {{ circle {{ stroke: #0d1117; }} }}
  </style>
  <line class="baseline" x1="{left}" y1="{bottom}" x2="{right}" y2="{bottom}"/>
  <path class="area" d="{area_path}"/>
  <path class="line" d="{line_path}"/>
  <g>{dots}</g>
  <g>{''.join(labels)}</g>
</svg>
'''


def atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(content, encoding="utf-8")
    temporary.replace(path)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--username", default=os.getenv("GITHUB_REPOSITORY_OWNER", "fo9c"))
    parser.add_argument("--output", type=Path, default=Path("assets/activity-graph.svg"))
    parser.add_argument("--days", type=int, default=31)
    parser.add_argument("--input-json", type=Path)
    args = parser.parse_args()

    if args.days < 2:
        parser.error("--days must be at least 2")

    if args.input_json:
        payload = json.loads(args.input_json.read_text(encoding="utf-8"))
    else:
        token = os.getenv("GITHUB_TOKEN")
        if not token:
            parser.error("GITHUB_TOKEN is required unless --input-json is supplied")
        payload = fetch_contributions(args.username, token)

    contributions, total = parse_contributions(payload, args.days)
    svg = render_svg(args.username, contributions, total)
    atomic_write(args.output, svg)
    print(f"Generated {args.output} with {len(contributions)} days and {total} contributions")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
