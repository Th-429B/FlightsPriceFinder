import json
import time
import traceback
from datetime import datetime, timedelta
from pathlib import Path

import finder
import notifier

CONFIG_FILE = Path(__file__).parent / "config.json"
DATE_FMT = "%Y-%m-%d"


def flex_dates(center: str, flex_days: int) -> list[str]:
    """All dates from center-flex to center+flex, inclusive."""
    center_date = datetime.strptime(center, DATE_FMT).date()
    return [
        (center_date + timedelta(days=offset)).strftime(DATE_FMT)
        for offset in range(-flex_days, flex_days + 1)
    ]


def search_route(route: dict) -> str:
    """Search every depart/return permutation in the flex window and
    return a Telegram message with the top 3 cheapest combinations."""
    start, end = route["start"], route["end"]
    flex = route.get("flex_days", 0)
    depart_options = flex_dates(route["depart"], flex)
    return_options = flex_dates(route["return"], flex)

    results = []
    failures = 0
    for depart in depart_options:
        for ret in return_options:
            if depart >= ret:
                continue
            try:
                cheapest = finder.find_round_trip(
                    start, end, depart, ret, max_stops=route.get("max_stops", 0)
                )
                if cheapest is not None:
                    results.append((depart, ret, cheapest))
            except Exception:
                failures += 1
            time.sleep(1)

    results.sort(key=lambda item: finder._price_value(item[2]))

    lines = [
        f"✈️ *{start} ⇄ {end}* round trips",
        f"Depart {depart_options[0]} … {depart_options[-1]}, "
        f"return {return_options[0]} … {return_options[-1]}",
        "",
    ]
    for i, (depart, ret, flight) in enumerate(results[:3], 1):
        name = flight.name or "Unknown airline"
        lines.append(f"*{i}. {depart} → {ret}* — {flight.price}")
        lines.append(f"    {name}")
        if flight.departure and flight.arrival:
            if flight.stops == 0:
                stops = "non-stop"
            elif isinstance(flight.stops, int):
                stops = f"{flight.stops} stop(s)"
            else:
                stops = "stops unknown"
            lines.append(
                f"    Outbound: {flight.departure} → {flight.arrival}"
                f" ({flight.duration}, {stops})"
            )
    if not results:
        lines.append("No flights found in the window.")
    if failures:
        lines.append(f"\n_({failures} of the date searches failed)_")
    return "\n".join(lines)


def main():
    config = json.loads(CONFIG_FILE.read_text())

    for route in config["routes"]:
        try:
            message = search_route(route)
        except Exception:
            message = (
                f"⚠️ Flight search failed for {route.get('start')} → {route.get('end')}:\n"
                f"```\n{traceback.format_exc(limit=3)}```"
            )
        notifier.send_telegram(message)


if __name__ == "__main__":
    main()
