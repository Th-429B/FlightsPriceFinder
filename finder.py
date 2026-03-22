from fast_flights import FlightData, Passengers, Result, get_flights
import json_convertor
import arg_parser

start_country, end_country, date, debug = arg_parser.parse_args()


result: Result = get_flights(
    flight_data=[
        FlightData(date=date, from_airport=end_country, to_airport=start_country, max_stops=0)
    ],
    trip="one-way",
    seat="economy",
    passengers=Passengers(adults=1),
    fetch_mode="fallback",
)

price_status = result.current_price
top_5_flights = result.flights[0:5]

if debug:
    print(price_status)
    print(json_convertor.json_prettier(top_5_flights))
