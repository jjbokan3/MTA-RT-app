# %%
# IMPORTS
import requests

import gtfs_realtime_NYCT_pb2
import gtfs_realtime_pb2
import polars as pl
from polars import col
import re
from PIL import Image
import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import plotly.graph_objects as go
import pandas as pd
from PIL import Image
import pyarrow
import json
import bisect
import math
from datetime import datetime, timedelta
import plotly.io as pio

# %% [markdown]
# ## Read in Flat Files

# %%
# FLAT FILE IMPORT
stops = pl.read_csv(
    "stops.txt",
    separator=",",
    has_header=True,
    schema_overrides={"parent_station": pl.String},
)

shapes = pl.read_csv(
    "shapes.txt",
    separator=",",
    has_header=True,
)

colors = pl.read_csv("MTA_Colors_20240623.csv", separator=",", has_header=True)

# %%
# READ IN MAP

# Load the plot from an HTML file
with open("map_plot.json", "r") as f:
    fig_json = json.load(f)

fig = go.Figure(fig_json)

# %% [markdown]
# ## Constants

# %%
STOP_STATUS = {"0": "Incoming At", "1": "Stopped At", "2": "In Transit To"}

# %%
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

# %%
response = requests.get(API_ENDPOINTS["1234567"])
feed = gtfs_realtime_pb2.FeedMessage()
feed.ParseFromString(response.content)

# %% [markdown]
# ## Functions

# %%
def plot_map(
    coordinates,
    fig,
    trip_id,
    line,
    # hovertext,
    marker_size=15,
    marker_color="#03fca9",
):

    fig.add_trace(
        go.Scattermapbox(
            mode="markers+text",
            name=trip_id,
            lon=[coordinates[0]],
            lat=[coordinates[1]],
            text=line,
            textfont=dict(color="#ffffff"),
            marker={
                "size": marker_size,
                "color": color_lookup[line],
                # "symbol": "triangle-up",
            },
            showlegend=False,
            hoverinfo="text",
            hovertext=f"<b>Line {line}<b><br>{coordinates}",
        )
    )
    # fig.add_annotation(
    #     go.layout.Annotation(
    #         text=trip_id,
    #         showarrow=False,
    #         x=coordinates[0],
    #         y=coordinates[1],
    #         xref="x",
    #         yref="y",
    #         font=dict(size=12, color="black"),
    #         xanchor="center",
    #         yanchor="middle",
    #     )
    # )

# %%
def haversine(lat1, lon1, lat2, lon2):
    R = 6371  # Earth radius in kilometers
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    distance = R * c
    return distance

# %%
# Define a function to calculate distance using lead coordinates
def calculate_distance_within_line(df):

    df = df.sort("shape_pt_sequence")

    # Create lead columns for lat and lon
    df = df.with_columns(
        [
            df["shape_pt_lat"].shift(1).alias("lag_lat"),
            df["shape_pt_lon"].shift(1).alias("lag_lon"),
        ]
    )

    # Apply the Haversine function to each row and add the result as a new column
    return df.with_columns(
        [
            pl.concat_list(["shape_pt_lat", "shape_pt_lon", "lag_lat", "lag_lon"])
            .map_elements(
                lambda row: (
                    haversine(row[0], row[1], row[2], row[3])
                    if row[2] is not None and row[3] is not None
                    else None
                ),
                return_dtype=pl.Float64,
            )
            .alias("distance")
        ]
    )

# %%
def linear_distance(lon1, lat1, lon2, lat2, fraction):
    lat = lat1 + (lat2 - lat1) * fraction
    lon = lon1 + (lon2 - lon1) * fraction
    return lat, lon

# %%
def calculate_position(api_time, departure, arrival, df: pl.DataFrame, incoming=False):
    trip_time = arrival - departure
    since_departure = api_time - departure
    proportion_traveled = since_departure / trip_time
    # TODO: Calculate proportions in case a train is skipping a stop

    loc = bisect.bisect_left(
        (cum_sum := df["cum_sum"].fill_null(0).to_list()), proportion_traveled
    )

    temp = df[loc, :][0].to_dict(as_series=False)
    if incoming:
        return linear_distance(
            temp["lag_lon"][0],
            temp["lag_lat"][0],
            temp["shape_pt_lon"][0],
            temp["shape_pt_lat"][0],
            0.9,
        )
    elif proportion_traveled in cum_sum:
        return df[loc, :].select(["shape_pt_lat", "shape_pt_lon"]).row(0)
    else:
        return linear_distance(
            temp["lag_lon"][0],
            temp["lag_lat"][0],
            temp["shape_pt_lon"][0],
            temp["shape_pt_lat"][0],
            (proportion_traveled - (cum_sum[loc - 1] if loc != 1 else 0))
            / (cum_sum[loc] - cum_sum[loc - 1]),
        )

# %% [markdown]
# ## Color cleaning

# %%
colors = colors.filter(col("Operator") == "New York City Subway")
colors = colors.with_columns(
    col("Service").str.split(",")
)  # Split the comma-delimited values into lists
colors = colors.explode("Service")  # Explode the lists into separate rows

# %%
colors

# %%
color_lookup = colors.select(["Service", "Hex color"]).to_dict(as_series=False)
color_lookup = {x: y for (x, y) in zip(*color_lookup.values())}

# %% [markdown]
# ## Shape Cleaning

# %%
shape_unpack_re = re.compile(r"^(\w{1}).*\.+(\w+?)([XR]).*$")


def shape_unpack(shape):
    m = re.match(shape_unpack_re, shape)
    return m.group(1), m.group(2)


shapes_clean = shapes.with_columns(
    [
        shapes["shape_id"]
        .map_elements(lambda x: shape_unpack(x)[0], return_dtype=str)
        .alias("Line"),
        shapes["shape_id"]
        .map_elements(lambda x: shape_unpack(x)[1], return_dtype=str)
        .alias("Line_Variation"),
    ]
)

# %% [markdown]
# ## Stops Cleaning

# %%
stop_removal_re = r".*[NS]$"

stops = stops.filter(~stops["stop_id"].str.contains(stop_removal_re))

# %%
stop_unpack_re = re.compile(r"^(\w{1})(\d{2})")


def stop_unpack(stop):
    m = re.match(stop_unpack_re, stop)
    return m.group(1), m.group(2)


stops_clean = stops[["stop_id", "stop_name", "stop_lat", "stop_lon"]].with_columns(
    [
        stops["stop_id"]
        .map_elements(lambda x: stop_unpack(x)[0], return_dtype=str)
        .alias("Line"),
        stops["stop_id"]
        .map_elements(lambda x: stop_unpack(x)[1], return_dtype=str)
        .alias("Order"),
    ]
)

# %%
# stops_clean = stops_clean.join(line_points, left_on="Line", right_on="Line", how="left")
stops_clean = (
    stops_clean.join(colors, left_on="Line", right_on="Service", how="left")
    .with_columns(pl.col("Hex color").fill_null("#858585"))
    .select(
        ["stop_name", "stop_id", "stop_lat", "stop_lon", "Line", "Order", "Hex color"]
    )
)

# %%
stop_lookup = stops_clean.select(["stop_id", "stop_lon", "stop_lat"]).to_dict(
    as_series=False
)
stop_lookup = {x: (y, z) for (x, y, z) in zip(*stop_lookup.values())}

# %% [markdown]
# ## Merge Shaps and Stops

# %%
shapes_final = shapes_clean.join(
    stops_clean.select(["stop_lon", "stop_lat", "stop_name", "stop_id"]),
    left_on=("shape_pt_lon", "shape_pt_lat"),
    right_on=("stop_lon", "stop_lat"),
    how="left",
)

# %% [markdown]
# ## Master train info

# %%
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
trains_tracked = {}
problems_log = []

# %%
def initialize_train_table(trains_tracked):
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
        if len(vehicle) == 0 and len(updates) == 0:
            problems_log[trip_id] = "Both"
            continue
        elif len(vehicle) == 0:
            problems_log[trip_id] = "Vehicle"
            continue
        elif len(updates) == 0:
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
        number_stop = re.compile(r"^(\d+)")
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


def update_train_table(trains_tracked):
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

# %%
trains_tracked = {}
problems_log = []
initialize_train_table(trains_tracked)

# %%
trains_tracked

# %%
stop_schedule = {}
stop_schedule = {stop_id: [] for stop_id in stops_clean["stop_id"].to_list()}

# %%
for trip, v in trains_tracked.items():
    train_stops = {
        stop[:-1]: dict(
            direction=v["current_direction"], line=v["line"], arrival=times["arrival"]
        )
        for stop, times in v["current_schedule"].items()
    }
    for stop, schedule in train_stops.items():
        stop_schedule[stop].append(schedule)

# %%
stop_schedule

# %%
stop_strings = {}
for stop, arrivals in stop_schedule.items():
    stop_string = ""
    lines = set([a["line"] for a in arrivals])
    for line in sorted(lines):
        arrivals_line = [
            arrival
            for arrival in arrivals
            if arrival["line"] == line
            and datetime.now() <datetime.fromtimestamp(arrival["arrival"])
            < datetime.now() + timedelta(minutes=30)
        ]
        arrivals_line_sorted = sorted(arrivals_line, key=lambda x: x["arrival"])
        stop_string += f"<b>{line.upper()}<b><br>"
        for arrival in arrivals_line:
            stop_string += f"{datetime.fromtimestamp(arrival['arrival']).strftime("%I:%M")}<br>"
        stop_strings[stop] = stop_string

# %%
stop_strings["127"]

# %%
stop_schedule = {
    stop[:-1]: dict(
        direction=v["current_direction"], trip_id=trip_id, arrival=times["arrival"]
    )
    for trip_id, v in trains_tracked.items()
    for stop, times in v["current_schedule"].items()
}

# %% [markdown]
# ## Testing

# %%
def route_to_shape(trip_id):
    # exact_route_to_shape = re.compile(r"^.*_(.*)$")
    route_to_shape = re.compile(r"^.*_(.*?)([RX]).*$")
    simple_route_to_shape = re.compile(r"^.*_(.*?\.{1,2}[NS]).*")
    shape = route_to_shape.search(trip_id)
    if shape:
        train_route = shapes_final.filter(pl.col("shape_id") == shape.groups(1)[0])
        if not train_route.is_empty():
            return train_route, shape[0]
    simple_shape = simple_route_to_shape.match(trip_id).groups(1)[0]
    partial_shape = [
        x
        for x in shapes_final["shape_id"].unique().to_list()
        if re.search(rf".*{simple_shape}.*", x)
    ][0]
    train_route = shapes_final.filter(pl.col("shape_id") == partial_shape)
    return train_route, partial_shape[0]

# %%
for trip_id in trains_tracked.keys():
    train_route, line = route_to_shape(trip_id)
    match trains_tracked[trip_id]["current_status"]:

        case 0:
            incoming = True
        case 1:
            plot_map(
                stop_lookup[trains_tracked[trip_id]["current_station"]],
                fig,
                trip_id,
                line,
            )
            continue

    # TODO: Implement beginning of trip versus mismatch of stations (symbol blinks red)
    if trains_tracked[trip_id]["prev_departure_station"] is None:
        continue
    prev_stop = train_route.select(
        [
            pl.arg_where(
                pl.col("stop_id") == trains_tracked[trip_id]["prev_departure_station"]
            ),
        ]
    )[0, 0]

    next_stop = train_route.select(
        [
            pl.arg_where(
                pl.col("stop_id") == trains_tracked[trip_id]["planned_next_station"]
            ),
        ]
    )[0, 0]
    in_route = train_route[prev_stop : next_stop + 1]
    result = in_route.group_by("Line", maintain_order=True).map_groups(
        calculate_distance_within_line
    )

    sums = result.select(pl.col("distance").drop_nulls()).to_series().sum()
    result = result.with_columns((result["distance"] / sums).alias("proportion"))
    result = result.with_columns(
        pl.col("proportion").cum_sum().round(7).alias("cum_sum")
    )
    api_time = trains_tracked[trip_id]["current_loc_info"].timestamp
    departure = trains_tracked[trip_id]["prev_departure_time"]
    arrival = trains_tracked[trip_id]["current_schedule"][0][0].arrival.time
    position = calculate_position(api_time, departure, arrival, result, incoming)
    plot_map(position, fig, trip_id, line)
    break

# %% [markdown]
# # Plotting Train

# %%
for stop in stop_lookup.keys():
    try:
        fig.update_traces(selector=dict(name=stop), text=stop_strings[str(stop)])
    except KeyError:
        continue
for trip in trains_tracked.keys():
    fig.update_traces(
        selector=dict(name=trip),
        hovertext=f"Next Stop: {trains_tracked[trip]['planned_next_station']}",
    )

# %%
app = dash.Dash(__name__)

app.layout = html.Div([dcc.Graph(id="live-map", figure=fig)])

if __name__ == "__main__":
    app.run_server(debug=True)

# %%
trains_tracked

# %%


