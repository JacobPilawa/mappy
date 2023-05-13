# Import the required libraries
import os
import gpxpy
import base64
import plotly.graph_objects as go
import numpy as np
import matplotlib.cm as cm
import dash
from dash import dcc, html
from dash.dependencies import Input, Output
from math import radians, sin, cos, sqrt, atan2

app = dash.Dash(__name__)

# Function to transform the filename into a readable label
def transform_name(name):
    name = name[2:-4]
    lab = name[0:-4] + '/' + \
          name[-4:-2] + '/' + \
          name[-2:]
    return lab
	 
def calculate_distance(lat1, lon1, lat2, lon2):
    R = 3963.19  # Radius of the Earth in kilometers
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    dist = R * c
    return dist

# Function to read GPX files and extract route data
def read_gpx(file_path):
    with open(file_path, 'r') as gpx_file:
        gpx = gpxpy.parse(gpx_file)

        route_info = []
        for track in gpx.tracks:
            name = track.name
            for segment in track.segments:
                for point in segment.points:
                    route_info.append([point.latitude, point.longitude, point.elevation])

        return route_info

# Create the map
map_berkeley = go.Figure(go.Scattermapbox())

map_berkeley.update_layout(
    mapbox={
        "style": "stamen-terrain",  # Choose your desired mapbox style here
        "center": {"lat": 37.87754, "lon": -122.276},
        "zoom": 13,
    },
    margin={"l": 0, "r": 0, "t": 0, "b": 0},
    height=600,
    width=1200,
    clickmode="event+select"  # Enable click events on the plot
)

routes_dir = '../data/'
colormap = cm.get_cmap('gnuplot2')  # Choose your desired colormap here
legend_entries = []
# Sort the filenames
sorted_files = sorted([file_name for file_name in os.listdir(routes_dir) if file_name.endswith('.gpx')])

for i, file_name in enumerate(sorted_files):
    route_path = os.path.join(routes_dir, file_name)
    route_data = read_gpx(route_path)

    # Generate color from the colormap
    color = colormap(i / len(sorted_files))
    hex_color = '#%02x%02x%02x' % (int(color[0] * 255), int(color[1] * 255), int(color[2] * 255))

    # Create a Scattermapbox trace for the route
    route_trace = go.Scattermapbox(
        lat=[point[0] for point in route_data],
        lon=[point[1] for point in route_data],
        mode='lines',
        line=dict(color=hex_color, width=5),
        hoverinfo='text',  # Set hoverinfo to 'text'
        text=file_name,  # Set the filename as the hover text
        customdata=[route_path],
        name=file_name,
    )
    # Add the trace to the map
    map_berkeley.add_trace(route_trace)

    # Add a legend entry for the route
    legend_entry = dict(
        label=transform_name(file_name),
        color=hex_color
    )
    legend_entries.append(legend_entry)

# Create the legend
legend_style = {
    "position": "absolute",
    "bottom": "20px",
    "left": "20px",
    "padding": "10px",
    "background-color": "white",
    "border": "1px solid grey",
}

# Create buttons to turn on/off all routes
button_style_on = {
    "margin": "5px",
    "font-size": "20px",
    "color": "white",
    "border-radius": "8px",
    "background-color": "#4CAF50",
    "opacity": "0.9"
}

button_style_off = {
    "margin": "5px",
    "font-size": "20px",
    "color": "white",
    "border-radius": "8px",
    "background-color": "#f44336",
    "opacity": "0.9"
}

turn_on_button = html.Button("Turn On All Routes", id="turn-on-button", style=button_style_on)
turn_off_button = html.Button("Turn Off All Routes", id="turn-off-button", style=button_style_off)
plot_button = html.Button("Print Visible Routes", id="print-routes-button", style=button_style_on)

# Create the elevation vs. distance subplot
elevation_figure = go.Figure()

elevation_figure.update_layout(
    margin={"l": 0, "r": 0, "t": 0, "b": 0},
    height=600,
    clickmode="event+select"  # Enable click events on the plot
)

# Create the app layout
app.layout = html.Div([	
	html.Div([
		turn_on_button,
		turn_off_button
	], style={"margin-top": "0px","text-align": "right"}),
	html.Hr(),
	html.Div([
		html.Div([
			dcc.Graph(
				id="map",
				figure=map_berkeley
			),
			html.Hr(),
			html.Div([
				plot_button,
			], style={"margin-top": "0px","text-align": "right"}),
			dcc.Graph(
				id="elevation",
				figure=elevation_figure
			)
		], style={"display": "inline-block", "width": "100%"}),
	])
])

# Callback to handle turning on/off all routes and handling click events
@app.callback(
    [Output("map", "figure"), Output("map", "selectedData"), Output("elevation", "figure")],
    [Input("turn-on-button", "n_clicks"), Input("turn-off-button", "n_clicks"), Input("map", "clickData")]
)
def handle_route_visibility(turn_on_clicks, turn_off_clicks, click_data):
    triggered_button_id = dash.callback_context.triggered[0]["prop_id"].split(".")[0]

    if triggered_button_id == "turn-on-button":
        for route_trace in map_berkeley.data:
            route_trace.visible = True
    elif triggered_button_id == "turn-off-button":
        for route_trace in map_berkeley.data:
            route_trace.visible = "legendonly"

    if click_data:
        points = click_data["points"]
        file_path = points[0]["customdata"]

        # Get the current visibility state of all routes
        visibility = [route_trace.visible for route_trace in map_berkeley.data]

        # Toggle the visibility of the clicked route
        route_index = next((i for i, trace in enumerate(map_berkeley.data) if trace["customdata"] == file_path), None)
        if route_index is not None:
           
            visibility[route_index] = not visibility[route_index]

        # Update the visibility states of all routes
        for i, route_trace in enumerate(map_berkeley.data):
            route_trace.visible = visibility[i]

        # Update the layout to reflect the changes
        map_berkeley.update_layout()

    # Filter the visible routes for plotting on the elevation subplot
    visible_routes = [route_trace for route_trace in map_berkeley.data if route_trace.visible==True][1:]

    # Create the elevation vs. distance subplot for visible routes
    elevation_figure = go.Figure()
    for route_trace in visible_routes:
        route_data = read_gpx(route_trace["customdata"][0])
        distances = []
        distances.append(0)
        elevations = []
        distance = 0
        for i in range(1, len(route_data)):
            lat1, lon1, _ = route_data[i - 1]
            lat2, lon2, ele2 = route_data[i]
            distance += calculate_distance(lat1, lon1, lat2, lon2)
            distances.append(distance)
            elevations.append(ele2)

        elevation_trace = go.Scatter(
            x=distances,
            y=elevations,
            mode='lines',
            line=dict(color=route_trace["line"]["color"], width=2),
            name=route_trace["name"]
        )
        elevation_figure.add_trace(elevation_trace)

    # Configure the elevation subplot layout
    elevation_figure.update_layout(
        title="Profiles",
        xaxis_title="Distance (miles)",
        yaxis_title="Elevation (feet)",
        showlegend=True,
        legend=dict(
            x=1.02,
            y=1,
            xanchor="left",
            yanchor="top",
            bgcolor="white",
            bordercolor="gray",
            borderwidth=0,
            orientation="v"
        ),
        yaxis_range=[-10, 250],
		  xaxis_range=[-0.05,6]
    )

    return map_berkeley, None, elevation_figure


if __name__ == "__main__":
    app.run_server(debug=True, port=8051)
