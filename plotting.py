import re
import polars as pl
from cleaning import stop_lookup_f
from math_calculations import calculate_position, calculate_distance_within_line
import plotly.graph_objects as go

from stop_schedule import stop_strings_creation, stop_schedule_creation


def plot_map(
        coordinates,
        fig,
        trip_id,
        line,
        color_lookup,
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


def route_to_shape(trip_id, shapes_stops):
    # exact_route_to_shape = re.compile(r"^.*_(.*)$")
    route_to_shape = re.compile(r"^.*_(.*?)([RX]).*$")
    simple_route_to_shape = re.compile(r"^.*_(.*?\.{1,2}[NS]).*")
    shape = route_to_shape.search(trip_id)
    if shape:
        train_route = shapes_stops.filter(
            pl.col("shape_id") == shape.groups(1)[0]
        )
        if not train_route.is_empty():
            return train_route, shape[0]
    simple_shape = simple_route_to_shape.match(trip_id).groups(1)[0]
    simple_shape_x = str(simple_shape).replace("X", "")
    partial_shape = [
        x
        for x in shapes_stops["shape_id"].unique().to_list()
        if re.search(rf".*({simple_shape}|{simple_shape_x}).*", x)
    ][0]
    train_route = shapes_stops.filter(pl.col("shape_id") == partial_shape)
    return train_route, partial_shape[0]


# %%
def plot_trains(fig, trains_tracked, shapes_stops, color_lookup, stop_lookup):
    for trip_id in trains_tracked.keys():
        train_route, line = route_to_shape(trip_id, shapes_stops)
        match trains_tracked[trip_id]["current_status"]:

            case 0:
                incoming = True
            case 1:
                if stop := stop_lookup_f(
                        trains_tracked[trip_id]["current_station"], "coordinates", stop_lookup
                ):
                    plot_map(stop, fig, trip_id, line, color_lookup)
                continue

        # TODO: Implement beginning of trip versus mismatch of stations (symbol blinks red)
        if trains_tracked[trip_id]["prev_departure_station"] is None:
            continue
        prev_stop = train_route.select(
            [
                pl.arg_where(
                    pl.col("stop_id")
                    == trains_tracked[trip_id]["prev_departure_station"]
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
        in_route = train_route[prev_stop: next_stop + 1]
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
        plot_map(position, fig, trip_id, line, color_lookup)
        # break


def stop_info_plotting(fig, trains_tracked, stop_schedule, stop_lookup):
    stop_strings = stop_strings_creation(
        stop_schedule_creation(trains_tracked, stop_schedule)
    )
    for stop in stop_lookup.keys():
        try:
            fig.update_traces(selector=dict(name=stop), text=stop_strings[str(stop)])
        except KeyError:
            print("Stop key error")
            continue
    for trip in trains_tracked.keys():
        if next_stop := trains_tracked[trip]["planned_next_station"]:
            fig.update_traces(
                selector=dict(name=trip),
                # TODOOOOOOO: None is not subscriptable, better account for stations that don't exist
                hovertext=f"Next Stop: {stop_lookup_f(next_stop, 'name', stop_lookup)}<br>Direction: {trains_tracked[trip]['current_direction']}<br>Trip: {trip}",
            )
