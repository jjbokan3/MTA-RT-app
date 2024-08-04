from api_call import get_base_data
import re

API_ENDPOINTS = {
    "ACE": r"https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-ace",
    "BDFM": r"https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-bdfm",
    "G": r"https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-g",
    "JZ": r"https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-jz",
    "NQRW": r"https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-nqrw",
    "L": r"https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-l",
    "1234567": r"https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs",
    "SI": r"https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-si",
}


def departure_time(updates):
    try:
        return updates[0][0].departure.time
    except IndexError:
        return None


def get_stop(updates):
    try:
        return updates[0][0].stop_id
    except IndexError:
        return None


# %%
def initialize_train_table(trains_tracked, last_updated, problems_log):
    data = get_base_data(API_ENDPOINTS, last_updated)
    for feed in data.values():
        for trip_id in set(
            [x.vehicle.trip.trip_id for x in feed.entity if x.vehicle.trip.trip_id]
        ):

            vehicle = [
                x.vehicle
                for x in feed.entity
                if x.HasField("vehicle") and x.vehicle.trip.trip_id == trip_id
            ]
            updates = [
                x.trip_update.stop_time_update
                for x in feed.entity
                if x.HasField("trip_update") and x.trip_update.trip.trip_id == trip_id
            ]
            trip_details = [
                x.trip_update.trip
                for x in feed.entity
                if x.HasField("trip_update") and x.trip_update.trip.trip_id == trip_id
            ]

            # Avoids trains with missing information
            if len(vehicle) == 0 and len(updates[0]) == 0:
                problems_log[trip_id] = "Both"
                continue
            elif len(vehicle) == 0:
                problems_log[trip_id] = "Vehicle"
                continue
            elif len(updates[0]) == 0:
                problems_log[trip_id] = "Updates"
                continue

            vehicle = vehicle[0]
            updates = updates[0]
            trip_details = trip_details[0]

            updates_dict = {
                x.stop_id: {"arrival": x.arrival.time, "departure": x.departure.time}
                for x in updates
            }
            current_status = vehicle.current_status
            current_timestamp = vehicle.timestamp
            current_stop = vehicle.stop_id
            number_stop = re.compile(r"^(\w+)([NS]{1})")
            current_stop = number_stop.match(current_stop).groups(1)[0]
            if current_status == 1:
                if len(updates_dict) == 1:
                    trains_tracked[trip_id] = {
                        "prev_departure_time": current_timestamp,
                        "prev_departure_station": current_stop,
                        "planned_next_station": None,
                        "current_station": current_stop,
                        "current_schedule": updates_dict,
                        "current_status": current_status,
                        "current_timestamp": current_timestamp,
                        "current_direction": list(updates_dict.keys())[0][-1],
                        "line": trip_details.route_id,
                    }
                else:
                    trains_tracked[trip_id] = {
                        "prev_departure_time": current_timestamp,
                        "prev_departure_station": current_stop,
                        "planned_next_station": number_stop.match(
                            list(updates_dict.keys())[1]
                        ).groups(1)[0],
                        "current_station": current_stop,
                        "current_schedule": updates_dict,
                        "current_status": current_status,
                        "current_timestamp": current_timestamp,
                        "current_direction": list(updates_dict.keys())[0][-1],
                        "line": trip_details.route_id,
                    }
            elif current_status in (0, 2):
                # TODO: Implement if previous stop is not found, symbol appears red if previosly plotted
                if (
                    trip_id not in trains_tracked
                    or trains_tracked[trip_id]["planned_next_station"] != current_stop
                ):
                    trains_tracked[trip_id] = {
                        "prev_departure_time": None,
                        "prev_departure_station": None,
                        "planned_next_station": current_stop,
                        "current_station": current_stop,
                        "current_schedule": updates_dict,
                        "current_status": current_status,
                        "current_timestamp": current_timestamp,
                        "current_direction": list(updates_dict.keys())[0][-1],
                        "line": trip_details.route_id,
                    }
                else:
                    trains_tracked[trip_id]["current_timestamp"] = current_timestamp
                    trains_tracked[trip_id]["current_station"] = None
            else:
                if get_stop(updates) != trains_tracked[trip_id]["planned_next_station"]:
                    trains_tracked[trip_id]["prev_departure_station"] = trains_tracked[
                        trip_id
                    ]["next_station"]
                    trains_tracked[trip_id]["next_station"] = get_stop(updates)
                trains_tracked[trip_id]["current_schedule"] = updates

    return trains_tracked
