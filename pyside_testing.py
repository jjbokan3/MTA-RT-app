import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import plotly.express as px
import pandas as pd
import dash_bootstrap_components as dbc
from cleaning import shapes_stops_colors
import dash_table

def create_buttons(elements, num_cols=3):
    rows = []
    for i in range(0, len(elements), num_cols):
        row = dbc.Row([
            dbc.Col(dbc.Button(elements[j][0], id=f"btn-{elements[j][0]}", n_clicks=0, className='m-2 p-2', style={'color': '#ffffff', 'background-color': elements[j][1], 'border': 'none', 'font-family': 'helvetica', 'font-size': '32px', 'border-radius': '50%', 'width': '70px', 'height': '70px'}), width=4)
            for j in range(i, min(i + num_cols, len(elements)))
        ], justify='center')
        rows.append(row)
    return rows

# Sample data
df = pd.DataFrame({
    'lat': [37.7749, 34.0522, 40.7128],
    'lon': [-122.4194, -118.2437, -74.0060],
    'city': ['San Francisco', 'Los Angeles', 'New York']
})

shapes_stops, stop_lookup, color_lookup, stops_colors = shapes_stops_colors()

# Create the initial map figure
fig = px.scatter_mapbox(
    df, lat="lat", lon="lon", hover_name="city",
    zoom=3, height=600
)
fig.update_layout(mapbox_style="open-street-map", margin={"r":0,"t":0,"l":0,"b":0})

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

app.layout = dbc.Container([
    dbc.Row([
        dbc.Col(
            dcc.Graph(id='map', figure=fig, style={'width': '100%', 'height': '100%'}),
            width=6,
            className='p-0'
        ),
        dbc.Col([
            *create_buttons(list(color_lookup.items()))
        ], width=6, className='d-flex flex-column align-items-center justify-content-center'),
    ]),
    #     dbc.Col([
    #         dbc.Row([
    #             dbc.Col(dbc.Button('SF', id='btn-sf', n_clicks=0, color='primary', className='m-2 p-2', style={'border-radius': '50%', 'width': '70px', 'height': '70px'}), width=6),
    #             dbc.Col(dbc.Button('LA', id='btn-la', n_clicks=0, color='primary', className='m-2 p-2', style={'border-radius': '50%', 'width': '70px', 'height': '70px'}), width=6),
    #         ], justify='center'),
    #         dbc.Row([
    #             dbc.Col(dbc.Button('NY', id='btn-ny', n_clicks=0, color='primary', className='m-2 p-2', style={'border-radius': '50%', 'width': '70px', 'height': '70px'}), width=6),
    #             dbc.Col(dbc.Button('CHI', id='btn-chi', n_clicks=0, color='primary', className='m-2 p-2', style={'border-radius': '50%', 'width': '70px', 'height': '70px'}), width=6),
    #         ], justify='center'),
    #         dbc.Row([
    #             dbc.Col(dbc.Button('HOU', id='btn-hou', n_clicks=0, color='primary', className='m-2 p-2', style={'border-radius': '50%', 'width': '70px', 'height': '70px'}), width=6),
    #             dbc.Col(dbc.Button('PHX', id='btn-phx', n_clicks=0, color='primary', className='m-2 p-2', style={'border-radius': '50%', 'width': '70px', 'height': '70px'}), width=6),
    #         ], justify='center')
    #     ], width=6, className='d-flex flex-column align-items-center justify-content-center')
    # ]),
    dbc.Row([
        dbc.Col(
            dash_table.DataTable(
                id='table',
                columns=[{"name": i, "id": i} for i in df.columns],
                data=df.to_dict('records'),
                style_table={'height': '300px', 'overflowY': 'auto', 'width': '100%'},
                style_cell={
                    'textAlign': 'left',
                    'padding': '10px',
                    'backgroundColor': '#f9f9f9',
                    'color': '#333'
                },
                style_header={
                    'backgroundColor': '#e3e3e3',
                    'fontWeight': 'bold',
                    'color': '#333'
                }
            ),
            width=12,
            className='p-0'
        )
    ])
], fluid=True)

# @app.callback(
#     Output('map', 'figure'),
#     [Input('btn-sf', 'n_clicks'),
#      Input('btn-la', 'n_clicks'),
#      Input('btn-ny', 'n_clicks'),
#      Input('btn-chi', 'n_clicks'),
#      Input('btn-hou', 'n_clicks'),
#      Input('btn-phx', 'n_clicks')]
# )
def update_map(btn_sf, btn_la, btn_ny, btn_chi, btn_hou, btn_phx):
    ctx = dash.callback_context

    if not ctx.triggered:
        raise dash.exceptions.PreventUpdate

    button_id = ctx.triggered[0]['prop_id'].split('.')[0]

    if button_id == 'btn-sf':
        lat, lon, zoom = 37.7749, -122.4194, 10
    elif button_id == 'btn-la':
        lat, lon, zoom = 34.0522, -118.2437, 10
    elif button_id == 'btn-ny':
        lat, lon, zoom = 40.7128, -74.0060, 10
    elif button_id == 'btn-chi':
        lat, lon, zoom = 41.8781, -87.6298, 10
    elif button_id == 'btn-hou':
        lat, lon, zoom = 29.7604, -95.3698, 10
    elif button_id == 'btn-phx':
        lat, lon, zoom = 33.4484, -112.0740, 10

    fig.update_layout(mapbox_center={"lat": lat, "lon": lon}, mapbox_zoom=zoom)
    return fig

if __name__ == '__main__':
    app.run_server(debug=True)