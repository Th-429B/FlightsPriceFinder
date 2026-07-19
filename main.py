import json
import logging
import time
import traceback
from datetime import datetime, timedelta
from pathlib import Path

import finder
import notifier

CONFIG_FILE = Path(__file__).parent / "config.json"
DATE_FMT = "%Y-%m-%d"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)
# primp (fast_flights' HTTP client) logs every request URL at INFO
logging.getLogger("primp").setLevel(logging.WARNING)


def flex_dates(center: str, flex_days: int) -> list[str]:
    """All dates from center-flex to center+flex, inclusive."""
    center_date = datetime.strptime(center, DATE_FMT).date()
    return [
        (center_date + timedelta(days=offset)).strftime(DATE_FMT)
        for offset in range(-flex_days, flex_days + 1)
    ]


def with_day(date_str: str) -> str:
    """'2026-11-01' -> '2026-11-01 (Sun)'"""
    day = datetime.strptime(date_str, DATE_FMT).strftime("%a")
    return f"{date_str} ({day})"


def outbound_summary(flight) -> str:
    """One compact line for the outbound leg, e.g.
    'ZIPAIR Tokyo · 12:40 AM → 8:30 AM +1 (6 hr 50 min, non-stop)'."""
    name = flight.name or "Unknown airline"
    if not (flight.departure and flight.arrival):
        return name
    # Google's times look like '11:30 PM on Thu, Dec 10' — keep just the time,
    # the dates are already in the line above.
    dep = flight.departure.split(" on ")[0]
    arr = flight.arrival.split(" on ")[0]
    ahead = f" {flight.arrival_time_ahead}" if flight.arrival_time_ahead else ""
    if flight.stops == 0:
        stops = "non-stop"
    elif isinstance(flight.stops, int):
        stops = f"{flight.stops} stop(s)"
    else:
        stops = "stops unknown"
    return f"{name} · {dep} → {arr}{ahead} ({flight.duration}, {stops})"


def search_route(route: dict) -> str:
    """Search every depart/return permutation in the flex window and
    return a Telegram message with the top 5 cheapest combinations."""
    start, end = route["start"], route["end"]
    flex = route.get("flex_days", 0)
    depart_options = flex_dates(route["depart"], flex)
    return_options = flex_dates(route["return"], flex)

    pairs = [
        (d, r) for d in depart_options for r in return_options if d < r
    ]
    log.info(
        "Route %s -> %s: searching %d depart/return combinations",
        start, end, len(pairs),
    )

    results = []
    failures = 0
    for i, (depart, ret) in enumerate(pairs, 1):
        try:
            cheapest = finder.find_round_trip(
                start, end, depart, ret, max_stops=route.get("max_stops", 0)
            )
            if cheapest is None:
                log.warning("[%d/%d] %s -> %s: no flights found", i, len(pairs), depart, ret)
            else:
                results.append((depart, ret, cheapest))
                log.info(
                    "[%d/%d] %s -> %s: %s (%s)",
                    i, len(pairs), depart, ret,
                    cheapest.price, cheapest.name or "airline unknown",
                )
        except Exception as e:
            failures += 1
            log.error("[%d/%d] %s -> %s: search failed: %s", i, len(pairs), depart, ret, e)
        time.sleep(1)

    results.sort(key=lambda item: finder._price_value(item[2]))
    log.info(
        "Done: %d results, %d failures. Top result: %s",
        len(results), failures,
        f"{results[0][0]} -> {results[0][1]} at {results[0][2].price}" if results else "none",
    )

    lines = [
        f"✈️ *{start} ⇄ {end}* round trips",
        f"Depart {depart_options[0]}…{depart_options[-1]}, "
        f"return {return_options[0]}…{return_options[-1]}",
        "",
    ]
    for i, (depart, ret, flight) in enumerate(results[:5], 1):
        lines.append(f"*{i}. {with_day(depart)} → {with_day(ret)}* — {flight.price}")
        lines.append(f"    {outbound_summary(flight)}")
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
            log.exception("Route %s -> %s failed", route.get("start"), route.get("end"))
            message = (
                f"⚠️ Flight search failed for {route.get('start')} → {route.get('end')}:\n"
                f"```\n{traceback.format_exc(limit=3)}```"
            )
        notifier.send_telegram(message)
        log.info("Telegram message sent")


if __name__ == "__main__":
    main()
