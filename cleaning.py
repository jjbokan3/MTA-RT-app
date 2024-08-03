import polars as pl
from polars import col
import re


## Color cleaning
# %%
def color_file():
    colors = pl.read_csv("MTA_Colors_20240623.csv", separator=",", has_header=True)
    colors = colors.filter(col("Operator") == "New York City Subway")
    colors = colors.with_columns(
        col("Service").str.split(",")
    )  # Split the comma-delimited values into lists
    colors = colors.explode("Service")  # Explode the lists into separate rows
    # %%
    color_lookup = colors.select(["Service", "Hex color"]).to_dict(as_series=False)
    color_lookup = {x: y for (x, y) in zip(*color_lookup.values())}
    return colors, color_lookup


def shape_unpack(shape):
    shape_unpack_re = re.compile(r"^(\w{1}).*\.+(\w+?)([XR]).*$")
    m = re.match(shape_unpack_re, shape)
    return m.group(1), m.group(2)


def shapes_file():
    shapes = pl.read_csv(
        "shapes.txt",
        separator=",",
        has_header=True,
    )
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
    return shapes_clean


# %% md
## Stops Cleaning
# %%
def stop_direction_removal(stops):
    stop_removal_re = r".*[NS]$"

    stops = stops.filter(~stops["stop_id"].str.contains(stop_removal_re))


# %%


def stop_unpack(stop):
    stop_unpack_re = re.compile(r"^(\w{1})(\d{2})")
    m = re.match(stop_unpack_re, stop)
    return m.group(1), m.group(2)


def stops_file():
    stops = pl.read_csv(
        "stops.txt",
        separator=",",
        has_header=True,
        schema_overrides={"parent_station": pl.String},
    )
    stops = stop_direction_removal(stops)
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
    stop_lookup = stops_clean.select(
        ["stop_id", "stop_lon", "stop_lat", "stop_name"]
    ).to_dict(as_series=False)
    stop_lookup = {x: [(y, z), n] for (x, y, z, n) in zip(*stop_lookup.values())}
    return stops_clean, stop_lookup


# %%
# stops_clean = stops_clean.join(line_points, left_on="Line", right_on="Line", how="left")
# %%
# %%
def stop_lookup_f(stop, return_data, stop_lookup):
    if stop in ("R60", "R65", "X22", "M07", "H18"):
        return None
    else:
        try:
            if return_data == "coordinates":
                return stop_lookup[stop][0]
            elif return_data == "name":
                return stop_lookup[stop][1]
        except TypeError:
            print("TypeError")
            return None
        except KeyError:
            print(f"Key Error: {stop}")
            return None


# %% md
## Merge Shaps and Stops
# %%


def shapes_stops_colors():
    colors, color_lookup = color_file()
    shapes = shapes_file()
    stops, stop_lookup = stops_file()
    # stops_clean = (
    #     stops.join(colors, left_on="Line", right_on="Service", how="left")
    #     .with_columns(pl.col("Hex color").fill_null("#858585"))
    #     .select(
    #         [
    #             "stop_name",
    #             "stop_id",
    #             "stop_lat",
    #             "stop_lon",
    #             "Line",
    #             "Order",
    #             "Hex color",
    #         ]
    #     )
    # )
    shapes_stops_colors = shapes.join(
        stops_clean.select(["stop_lon", "stop_lat", "stop_name", "stop_id"]),
        left_on=("shape_pt_lon", "shape_pt_lat"),
        right_on=("stop_lon", "stop_lat"),
        how="left",
    )

    return shapes_stops_colors, stop_lookup, color_lookup
