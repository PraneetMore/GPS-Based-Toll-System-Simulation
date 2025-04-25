import geopandas as gpd

# Load the shapefile
road_network = gpd.read_file("D:\GPS TOLL\shapefiles\highway\mumbai_pune_road.shp")

# Convert to CSV
road_network.to_csv("road_network.csv", index=False)

# Display first few rows
print(road_network.head())
