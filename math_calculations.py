import math
import polars as pl
import bisect


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


def linear_distance(lon1, lat1, lon2, lat2, fraction):
    lat = lat1 + (lat2 - lat1) * fraction
    lon = lon1 + (lon2 - lon1) * fraction
    return lat, lon


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
