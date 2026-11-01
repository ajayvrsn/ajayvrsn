import json
import re
from html.parser import HTMLParser
from pathlib import Path
from urllib.request import Request, urlopen


USERNAME = "ajayvrsn"
OUTPUT = Path("data/contributions.json")


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
        if len(result) < 300:
            raise ValueError(f"Expected a full contribution calendar; found {len(result)} days")
        return sorted(result, key=lambda item: str(item["date"]))


def main() -> None:
    request = Request(
        f"https://github.com/users/{USERNAME}/contributions",
        headers={"User-Agent": "profile-readme-contribution-calendar"},
    )
    with urlopen(request, timeout=30) as response:
        page = response.read().decode("utf-8")

    parser = ContributionParser()
    parser.feed(page)
    days = parser.contributions()
    payload = {
        "username": USERNAME,
        "days": days,
    }

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"Saved {len(days)} contribution days to {OUTPUT}")


if __name__ == "__main__":
    main()
