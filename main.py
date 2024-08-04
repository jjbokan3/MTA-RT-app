import plotly.graph_objects as go
from train_table_creation import initialize_train_table
from plotting import plot_trains, stop_info_plotting
import dash
from dash import dcc, html
from dash.dependencies import Input, Output, State
import json
from cleaning import shapes_stops_colors
import re


# Function to generate the initial figure
def load_initial_figure(filename):
    with open(filename, "r") as f:
        fig_json = json.load(f)
    return go.Figure(fig_json)


# Callback function to update the map
def update_map_callback(n, fig_json, trains_tracked, last_updated, problems_log, stop_schedule, shapes_stops, color_lookup, stop_lookup):
    fig = go.Figure(fig_json)
    initialize_train_table(trains_tracked, last_updated, problems_log)
    print("Initialize Done")
    plot_trains(fig, trains_tracked, shapes_stops, color_lookup, stop_lookup)
    stop_info_plotting(fig, trains_tracked, stop_schedule, stop_lookup)
    return fig


# Main function to run the app
def main():
    app = dash.Dash(__name__)

    # Load initial figure
    fig_json = load_initial_figure("map_plot.json")
    fig = go.Figure(fig_json)

    # Define layout
    app.layout = html.Div(
        [
            dcc.Graph(
                id="live-map",
                figure=fig,
                style={"width": "50vw", "height": "50vw"},
            ),
            dcc.Interval(id="interval-component", interval=60 * 1000, n_intervals=0),
        ]
    )

    shapes_stops, stop_lookup, color_lookup, stops_colors = shapes_stops_colors()

    # Initialize state variables
    trains_tracked = {}
    problems_log = {}
    stop_schedule = {stop_id: [] for stop_id in list(stop_lookup.keys())}
    last_updated = {"last_updated": None}

    # trains_tracked = initialize_train_table(trains_tracked, last_updated, problems_log)

    # Define callback
    @app.callback(
        Output("live-map", "figure"),
        [Input("interval-component", "n_intervals")]
    )
    def update_map(n):
        return update_map_callback(n, fig_json, trains_tracked, last_updated, problems_log, stop_schedule, shapes_stops, color_lookup, stop_lookup)

    # Run the app
    app.run_server()

if __name__ == "__main__":
    main()