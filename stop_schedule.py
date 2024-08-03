from datetime import datetime, timedelta


def stop_schedule_creation(trains_tracked, stop_schedule):
    for trip, v in trains_tracked.items():
        train_stops = {
            stop[:-1]: dict(
                direction=v["current_direction"],
                line=v["line"],
                arrival=times["arrival"],
            )
            for stop, times in v["current_schedule"].items()
        }
        for stop, schedule in train_stops.items():
            try:
                stop_schedule[stop].append(schedule)
            except KeyError:
                # TODO: Implement logging here if stops dont seem to exist
                # i.e. R65N
                continue
    return stop_schedule


# %%
def stop_strings_creation(stop_schedule):
    stop_strings = {}
    for stop, arrivals in stop_schedule.items():
        stop_string = ""
        lines = set([a["line"] for a in arrivals])
        for line in sorted(lines):
            arrivals_line = [
                arrival
                for arrival in arrivals
                if arrival["line"] == line
                and datetime.now()
                < datetime.fromtimestamp(arrival["arrival"])
                < datetime.now() + timedelta(minutes=30)
            ]
            arrivals_line_sorted = sorted(arrivals_line, key=lambda x: x["arrival"])
            stop_string += f"<b>{line.upper()}<b><br>"
            for arrival in arrivals_line:
                stop_string += f"{datetime.fromtimestamp(arrival['arrival']).strftime("%I:%M")}<br>"
            stop_strings[stop] = stop_string
    return stop_strings
