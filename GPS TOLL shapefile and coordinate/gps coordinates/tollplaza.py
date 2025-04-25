import overpy
import pandas as pd

# Initialize Overpass API
api = overpy.Overpass()

# Corrected query without comments
query = """
[out:json];
(
  node["highway"="toll_booth"](18.5, 73.0, 19.5, 74.0);
  node["highway"="motorway_junction"]["exit"](18.5, 73.0, 19.5, 74.0);
  node["highway"="motorway_junction"]["entry"](18.5, 73.0, 19.5, 74.0);
);
out body;
"""

# Execute query
result = api.query(query)

# Extract data
points = []
for node in result.nodes:
    point_type = "Toll Plaza"
    if "exit" in node.tags:
        point_type = "Exit Point"
    elif "entry" in node.tags:
        point_type = "Entry Point"

    points.append({
        "name": node.tags.get("name", "Unknown"),
        "type": point_type,
        "lat": node.lat,
        "lon": node.lon
    })

# Save to CSV
df = pd.DataFrame(points)
df.to_csv("mumbai_pune_toll_entry_exit.csv", index=False)

# Print the extracted data
print(df)
