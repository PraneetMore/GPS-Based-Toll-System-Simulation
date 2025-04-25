import geopandas as gpd
import matplotlib.pyplot as plt

# Load the shapefile
shapefile_path = r"C:\Users\ACER\Documents\mumbai-pune .shp"

gdf = gpd.read_file(shapefile_path, encoding='ISO-8859-1')

# Plot the shapefile to visualize
gdf.plot(figsize=(10, 6), color='blue', linewidth=0.5)
plt.title("Mumbai-Pune Highway")
plt.show()

# Extract the geometry (linestring) for the highway
highway_geometry = gdf.geometry.iloc[0]  # Assuming a single highway feature

# Convert to a list of coordinates
coords = list(highway_geometry.coords)

# Display sample coordinates
print("GPS coordinates:", coords[:5])
