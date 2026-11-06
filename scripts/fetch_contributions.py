import json
import re
import sys
import time
from datetime import date, datetime
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlencode
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


USERNAME = "ajayvrsn"
OUTPUT = Path("data/contributions.json")
MAX_REQUEST_ATTEMPTS = 4
RETRYABLE_HTTP_CODES = {429, 500, 502, 503, 504}


def read_url(request: Request) -> bytes:
    for attempt in range(1, MAX_REQUEST_ATTEMPTS + 1):
        try:
            with urlopen(request, timeout=30) as response:
                return response.read()
        except HTTPError as error:
            if error.code not in RETRYABLE_HTTP_CODES or attempt == MAX_REQUEST_ATTEMPTS:
                raise
            reason = f"HTTP {error.code} {error.reason}"
        except URLError as error:
            if attempt == MAX_REQUEST_ATTEMPTS:
                raise
            reason = str(error.reason)

        delay = 2 ** (attempt - 1)
        print(
            f"GitHub request failed ({reason}); retrying in {delay}s "
            f"(attempt {attempt + 1}/{MAX_REQUEST_ATTEMPTS}).",
            file=sys.stderr,
        )
        time.sleep(delay)

    raise RuntimeError("GitHub request retries exhausted")


class ContributionParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.days: dict[str, dict[str, int | str]] = {}
        self.tooltips: dict[str, str] = {}
        self.current_tooltip: str | None = None
        self.tooltip_text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        if tag == "td" and "ContributionCalendar-day" in attributes.get("class", ""):
            date = attributes.get("data-date")
            level = attributes.get("data-level")
            element_id = attributes.get("id")
            if date and level is not None and element_id:
                self.days[element_id] = {
                    "date": date,
                    "level": int(level),
                    "count": 0,
                }
        elif tag == "tool-tip" and attributes.get("for"):
            self.current_tooltip = attributes["for"]
            self.tooltip_text = []

    def handle_data(self, data: str) -> None:
        if self.current_tooltip is not None:
            self.tooltip_text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "tool-tip" and self.current_tooltip is not None:
            self.tooltips[self.current_tooltip] = " ".join(self.tooltip_text)
            self.current_tooltip = None
            self.tooltip_text = []

    def contributions(self) -> list[dict[str, int | str]]:
        result = []
        for element_id, day in self.days.items():
            tooltip = self.tooltips.get(element_id)
            if tooltip is None:
                raise ValueError(f"GitHub omitted contribution details for {day['date']}")
            match = re.search(r"([\d,]+) contribution(?:s)? on ", tooltip)
            count = int(match.group(1).replace(",", "")) if match else 0
            result.append({**day, "count": count})
        return sorted(result, key=lambda item: str(item["date"]))


def fetch_contributions(start: date, end: date) -> list[dict[str, int | str]]:
    query = urlencode({"from": start.isoformat(), "to": end.isoformat()})
    request = Request(
        f"https://github.com/users/{USERNAME}/contributions?{query}",
        headers={"User-Agent": "profile-readme-contribution-calendar"},
    )
    page = read_url(request).decode("utf-8")

    parser = ContributionParser()
    parser.feed(page)
    days = [
        day
        for day in parser.contributions()
        if start <= date.fromisoformat(str(day["date"])) <= end
    ]
    expected_days = (end - start).days + 1
    if len(days) != expected_days:
        raise ValueError(
            f"GitHub returned {len(days)} of {expected_days} requested days "
            f"for {start} through {end}"
        )
    return days


def account_created_date() -> date:
    request = Request(
        f"https://api.github.com/users/{USERNAME}",
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "profile-readme-contribution-calendar",
        },
    )
    user = json.loads(read_url(request))
    created_at = user.get("created_at")
    if not isinstance(created_at, str):
        raise ValueError(f"GitHub did not return an account creation date for {USERNAME}")
    return datetime.fromisoformat(created_at.replace("Z", "+00:00")).date()


def main() -> None:
    today = date.today()
    created = account_created_date()
    days = []
    for year in range(created.year, today.year + 1):
        start = max(date(year, 1, 1), created)
        end = min(date(year, 12, 31), today)
        days.extend(fetch_contributions(start, end))

    payload = {
        "username": USERNAME,
        "days": days,
    }

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"Saved {len(days)} contribution days to {OUTPUT}")


if __name__ == "__main__":
    main()
