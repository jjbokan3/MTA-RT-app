import dash
from dash import dcc, html

app = dash.Dash(__name__)

colors = ["red", "blue", "green", "yellow", "purple", "orange", "pink", "cyan"]

app.layout = html.Div(
    [
        html.Div(
            [
                html.Button(
                    str(i + 1),
                    id=f"button-{i + 1}",
                    style={
                        "fontSize": "40px",
                        "borderRadius": "50%",
                        "width": "150px",
                        "height": "150px",
                        "backgroundColor": colors[i],
                        "display": "inline-block",
                        "margin": "2px",
                    },
                )
                for i in range(8)
            ],
            style={
                "display": "grid",
                "gridTemplateColumns": "repeat(2, max-content)",
                "gridGap": "2px",
                "justifyContent": "center",
                "alignItems": "center",
                "height": "60vh",
                "textAlign": "center",
            },
        )
    ]
)

if __name__ == "__main__":
    app.run_server(debug=True)
