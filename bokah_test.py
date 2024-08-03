import pandas as pd
import numpy as np
import string
import random

from bokeh.io import curdoc
from bokeh.models import ColumnDataSource, WMTSTileSource
from bokeh.plotting import figure
from bokeh.layouts import column
from math import pi


# Function to generate random coordinates within NYC area
def random_coordinates(n, lat_range, lon_range):
    latitudes = np.random.uniform(lat_range[0], lat_range[1], n)
    longitudes = np.random.uniform(lat_range[0], lon_range[1], n)
    return latitudes, longitudes


# Generate random letters for each point
n_points = 10
random_letters = [random.choice(string.ascii_uppercase) for _ in range(n_points)]


# Function to create a DataFrame with random coordinates
def create_random_data():
    lat_range = (40.55, 40.95)
    lon_range = (-74.15, -73.75)
    latitudes, longitudes = random_coordinates(n_points, lat_range, lon_range)
    return pd.DataFrame(
        {"latitude": latitudes, "longitude": longitudes, "letter": random_letters}
    )


# Initial random data
random_data = create_random_data()


# Convert latitude and longitude to Web Mercator coordinates
def lat_lon_to_web_mercator(df):
    k = 6378137
    df["x"] = df["longitude"] * (k * pi / 180.0)
    df["y"] = np.log(np.tan((90 + df["latitude"]) * pi / 360.0)) * k
    return df


random_data = lat_lon_to_web_mercator(random_data)

# Create a ColumnDataSource
source = ColumnDataSource(data=random_data)

# Create a figure with a custom tile source
tile_source = WMTSTileSource(
    url="https://basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}.png"
)

p = figure(
    x_range=(-8242000, -8210000),
    y_range=(4965000, 4995000),
    x_axis_type="mercator",
    y_axis_type="mercator",
    sizing_mode="stretch_both",
)
p.add_tile(tile_source)

# Add circles and text to the figure
p.circle(x="x", y="y", size=10, color="red", source=source)
p.text(
    x="x",
    y="y",
    text="letter",
    text_font_size="10pt",
    text_align="center",
    source=source,
)


# Update the data periodically
def update():
    new_data = create_random_data()
    new_data = lat_lon_to_web_mercator(new_data)
    source.data = new_data


# Add a periodic callback to update the data
curdoc().add_periodic_callback(update, 2000)

# Add the plot to the document
curdoc().add_root(column(p))
curdoc().title = "Real-Time Map Visualization"
