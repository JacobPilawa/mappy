import folium
import os
import gpxpy
import matplotlib.pyplot as plt
import base64
import matplotlib.cm as cm
from mpld3 import fig_to_html
from math import radians, sin, cos, sqrt, atan2
import json
import numpy as np

def transform_name(name):
    name = name[2:-4]
    lab = name[0:-4] + '/' + \
          name[-4:-2] + '/' + \
          name[-2:]
    return lab

# Define the Haversine function
def haversine(lat1, lon1, lat2, lon2):
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
                    route_info.append([point.latitude, point.longitude])
                    
        return route_info
    
def read_elevation(file_path):
    
    with open(file_path, 'r') as gpx_file:
        gpx = gpxpy.parse(gpx_file)
        
        route_info = []
        for track in gpx.tracks:
            name = track.name
            for segment in track.segments:
                for point in segment.points:
                    route_info.append([point.latitude, point.longitude, point.elevation])
    
    route_info = np.array(route_info)
    distance = 0
    distances = []
    distances.append(distance)
    for i in range(1, len(route_info[:,0])):
        # get current lat, lon
        lat1, lon1 = route_info[i-1,:][0],route_info[i-1,:][1]
        # get next lat, lon
        lat2, lon2 = route_info[i,:][0],route_info[i,:][1]
        # compute distance between these coords
        distance += haversine(lat1, lon1, lat2, lon2)
        distances.append(distance)
        
    # return distances, elevations
    return distances, route_info[:,-1]

def gen_fig_html(file_path,color):

    d, e = read_elevation(file_path)
    
    fig, ax = plt.subplots(nrows=1,ncols=1,figsize=(5,3),dpi=100)
    ax.plot(d,
            e*3.28084,
            lw=3,
            c=color,
            label=transform_name(file_path))
    ax.legend(loc='upper right')
    
    ax.minorticks_on()
    ax.grid(lw=0.5,ls='dotted')
    ax.set_xlabel('Distance [mi]')
    ax.set_ylabel('Elevation [feet]')
    ax.set_ylim(-10,700)

    # Save the figure as a temporary image file
    tmp_file = "data/image.png"  # Specify the path and filename of the temporary image file
    plt.savefig(tmp_file, format="png",bbox_inches='tight')
    plt.close()

    # Read the temporary image file and convert it to base64
    with open(tmp_file, "rb") as f:
        img_data = f.read()
        base64_img = base64.b64encode(img_data).decode("utf-8")

    # Generate the HTML code to embed the image
    html_code = f'<img src="data:image/png;base64,{base64_img}" />'

    # Display or save the HTML code as desired
    return html_code

# Function to handle click event on the route or legend entry
def on_click_route(event):
    route_polyline = event.target
    route_data = route_polyline.locations
    
    # Plot the elevation profile for the clicked route (example code)
    # Replace this with your actual code to plot the elevation profile
    elevation_profile = calculate_elevation_profile(route_data)
    plot_elevation_profile(elevation_profile)

# Create the map
map_berkeley = folium.Map(location=[37.87754, -122.276], 
                          tiles='openstreetmap',
                          zoom_start=14)

routes_dir = './data/'

colormap = cm.get_cmap('gnuplot2')  # Choose your desired colormap here

legend_html = '''
    <div style="position: fixed; bottom: 50px; right: 50px; background-color: white;
                border: 1px solid grey; padding: 10px; z-index: 1000;">
        <h4>Running Routes</h4>
        <ul style="list-style-type: none; padding-left: 0;">
'''

legend_entries = []

# Sort the filenames
sorted_files = sorted([file_name for file_name in os.listdir(routes_dir) if file_name.endswith('.gpx')])

for i, file_name in enumerate(sorted_files):
    route_path = os.path.join(routes_dir, file_name)
    route_data = read_gpx(route_path)

    # Generate color from the colormap
    color = colormap(i / len(sorted_files))
    hex_color = '#%02x%02x%02x' % (int(color[0] * 255), int(color[1] * 255), int(color[2] * 255))
    
    # Let's create the vincent chart.
    popup = gen_fig_html(route_path,color)

    iframe = folium.IFrame(popup)
    popup = folium.Popup(iframe,
                         min_width=500,
                         max_width=500)
    
    # Create a PolyLine on the map for the route
    line = route_polyline = folium.PolyLine(
        locations=route_data,
        color=hex_color,
        weight=5,
        opacity=0.8,
        fill=False,
        popup=popup,
    )
    

    # Add the route polyline to the map
    map_berkeley.add_child(route_polyline)

    # Add the route filename and line segment to the legend
    line_segment = f'<span style="background-color: {hex_color}; display: inline-block; width: 10px; height: 2px; margin-right: 5px;"></span>'
    legend_entry = f'<li>{line_segment}<span style="color: {hex_color};">{file_name}</span></li>'
    legend_entries.append(legend_entry)

# Add the legend entries to the legend HTML
legend_html += '\n'.join(legend_entries)
legend_html += '''
        </ul>
    </div>
'''

# Add the legend HTML to the map
map_berkeley.get_root().html.add_child(folium.Element(legend_html))

# Display the map
map_berkeley.save('map.html')