import re

from fast_flights import FlightData, Passengers, Result, get_flights


def _price_value(flight) -> float:
    """Extract a numeric value from a price string like 'SGD 256'."""
    match = re.search(r"[\d,]+", flight.price)
    return float(match.group().replace(",", "")) if match else float("inf")


def find_round_trip(start: str, end: str, depart_date: str, return_date: str, max_stops: int = 0):
    """Search round-trip flights for one specific depart/return date pair.

    Returns the cheapest flight option (price is the round-trip total),
    or None if the search returned nothing.
    """
    # Google intermittently (~1 in 5 fetches) serves a page variant where
    # only prices are parseable, leaving name/timing blank. Retry a few
    # times for a complete result; a degraded one is kept as last resort.
    best = None
    for _ in range(3):
        best = _search_round_trip(start, end, depart_date, return_date, max_stops)
        if best is not None and best.name:
            break
    return best


def _search_round_trip(start, end, depart_date, return_date, max_stops):
    result: Result = get_flights(
        flight_data=[
            FlightData(date=depart_date, from_airport=start, to_airport=end, max_stops=max_stops),
            FlightData(date=return_date, from_airport=end, to_airport=start, max_stops=max_stops),
        ],
        trip="round-trip",
        seat="economy",
        passengers=Passengers(adults=1),
        fetch_mode="fallback",
    )

    priced = [f for f in result.flights if _price_value(f) != float("inf")]
    return min(priced, key=_price_value, default=None)


def find_flights(start: str, end: str, date: str, max_stops: int = 0, top_n: int = 5):
    """Search one-way flights from start to end on date (YYYY-MM-DD).

    Returns (price_status, flights) where flights is the top_n cheapest results.
    """
    result: Result = get_flights(
        flight_data=[
            FlightData(date=date, from_airport=start, to_airport=end, max_stops=max_stops)
        ],
        trip="one-way",
        seat="economy",
        passengers=Passengers(adults=1),
        fetch_mode="fallback",
    )

    # The scrape often returns the same flight twice (once per page section).
    seen = set()
    unique = []
    for f in result.flights:
        key = (f.name, f.departure, f.price)
        if key not in seen:
            seen.add(key)
            unique.append(f)

    cheapest = sorted(unique, key=_price_value)
    return result.current_price, cheapest[:top_n]


if __name__ == "__main__":
    import arg_parser
    import json_convertor

    start, end, date, debug = arg_parser.parse_args()
    price_status, flights = find_flights(start, end, date)
    print(price_status)
    print(json_convertor.json_prettier(flights))
