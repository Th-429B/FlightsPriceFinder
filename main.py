import json
import logging
import time
import traceback
from datetime import date, datetime, timedelta
from pathlib import Path

import chart
import finder
import history
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


def leg_summary(flight) -> str:
    """One compact line for a leg, e.g. 'ZIPAIR Tokyo · 12:40 AM → 8:30 AM +1'."""
    name = flight.name or "Unknown airline"
    if not (flight.departure and flight.arrival):
        return name
    # Google's times look like '11:30 PM on Thu, Dec 10' — keep just the time,
    # the dates are already in the line above.
    dep = flight.departure.split(" on ")[0]
    arr = flight.arrival.split(" on ")[0]
    ahead = f" {flight.arrival_time_ahead}" if flight.arrival_time_ahead else ""
    return f"{name} · {dep} → {arr}{ahead}"


def currency_of(flight) -> str:
    """'SGD 913' -> 'SGD'"""
    head = flight.price.replace("\xa0", " ").split(" ")[0]
    return head if not head[:1].isdigit() else ""


def search_leg_dates(start: str, end: str, dates: list[str], max_stops: int):
    """One-way search for each date; returns {date: cheapest_flight}."""
    legs = {}
    failures = 0
    for i, date in enumerate(dates, 1):
        try:
            flight = finder.find_one_way(start, end, date, max_stops=max_stops)
            if flight is None:
                log.warning("[%d/%d] %s -> %s on %s: no flights", i, len(dates), start, end, date)
            else:
                legs[date] = flight
                log.info(
                    "[%d/%d] %s -> %s on %s: %s (%s)",
                    i, len(dates), start, end, date,
                    flight.price, flight.name or "airline unknown",
                )
        except Exception as e:
            failures += 1
            log.error("[%d/%d] %s -> %s on %s: failed: %s", i, len(dates), start, end, date, e)
        time.sleep(1)
    return legs, failures


def search_route(route: dict):
    """Search every depart/return permutation in the flex window.

    Returns (message, records): the Telegram message with the top 5
    cheapest combinations, and one history record per combination."""
    start, end = route["start"], route["end"]
    flex = route.get("flex_days", 0)
    depart_options = flex_dates(route["depart"], route.get("depart_flex_days", flex))
    return_options = flex_dates(route["return"], route.get("return_flex_days", flex))

    max_stops = route.get("max_stops", 0)
    log.info(
        "Route %s <-> %s: searching %d outbound + %d return one-way legs",
        start, end, len(depart_options), len(return_options),
    )
    out_legs, out_failures = search_leg_dates(start, end, depart_options, max_stops)
    ret_legs, ret_failures = search_leg_dates(end, start, return_options, max_stops)
    failures = out_failures + ret_failures

    # Legs price independently, so every combination is just the sum.
    results = [
        (d, r, out_legs[d], ret_legs[r])
        for d in out_legs
        for r in ret_legs
        if d < r
    ]
    results.sort(key=lambda x: finder._price_value(x[2]) + finder._price_value(x[3]))
    log.info(
        "Done: %d combinations from %d searches, %d failures",
        len(results), len(out_legs) + len(ret_legs), failures,
    )

    lines = [
        f"✈️ *{start} ⇄ {end}*",
        f"Depart {depart_options[0]}…{depart_options[-1]}, "
        f"return {return_options[0]}…{return_options[-1]}",
        "",
    ]
    for i, (depart, ret, out, back) in enumerate(results[:5], 1):
        total = finder._price_value(out) + finder._price_value(back)
        currency = currency_of(out) or currency_of(back)
        lines.append(
            f"*{i}. {with_day(depart)} → {with_day(ret)}* — {currency} {total:g}"
        )
        lines.append(f"    Out: {leg_summary(out)}")
        lines.append(f"    Back: {leg_summary(back)}")
    if not results:
        lines.append("No flights found in the window.")
    if failures:
        lines.append(f"\n_({failures} of the date searches failed)_")

    today = date.today().strftime(DATE_FMT)
    records = [
        {
            "run_date": today,
            "start": start,
            "end": end,
            "depart": d,
            "return": r,
            "total": finder._price_value(out) + finder._price_value(back),
            "currency": currency_of(out) or currency_of(back),
        }
        for d, r, out, back in results
    ]
    return "\n".join(lines), records


def main():
    config = json.loads(CONFIG_FILE.read_text())

    for route in config["routes"]:
        records = []
        try:
            message, records = search_route(route)
        except Exception:
            log.exception("Route %s -> %s failed", route.get("start"), route.get("end"))
            message = (
                f"⚠️ Flight search failed for {route.get('start')} → {route.get('end')}:\n"
                f"```\n{traceback.format_exc(limit=3)}```"
            )
        notifier.send_telegram(message)
        log.info("Telegram message sent")

        if records:
            history.append(records)
            log.info("History updated (%d rows)", len(records))
            chart_path = str(Path(__file__).parent / "trend.png")
            if chart.render(history.for_route(route["start"], route["end"]), chart_path):
                notifier.send_photo(
                    chart_path,
                    caption=f"{route['start']} ⇄ {route['end']} price trend",
                )
                log.info("Trend chart sent")


if __name__ == "__main__":
    main()
