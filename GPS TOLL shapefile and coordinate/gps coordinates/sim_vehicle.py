import geopandas as gpd
import pandas as pd
import random
import datetime
import json
from shapely.geometry import Point, LineString
from geopy.distance import geodesic

# File paths
toll_plazas_file = r"D:\GPS TOLL\gps coordinates\toll_plazas.csv"
road_network_file = r"D:\GPS TOLL\shapefiles\highway\mumbai_pune_road.shp"
toll_pricing_file = r"D:\GPS TOLL\gps coordinates\toll_pricing.csv"
route_csv_file = r"D:\GPS TOLL\shapefiles\route.csv"
output_csv_file = r"D:\GPS TOLL\gps coordinates\vehicle_movements.csv"

# Load Data
try:
    toll_plazas = pd.read_csv(toll_plazas_file)
    road_network = gpd.read_file(road_network_file)
    toll_pricing = pd.read_csv(toll_pricing_file)
    route_df = pd.read_csv(route_csv_file)
    print("✅ Data Loaded Successfully!")
except Exception as e:
    print(f"❌ Error loading data: {e}")
    exit()

# Ensure required columns exist
required_cols = {"Latitude", "Longitude", "Name"}
if not required_cols.issubset(set(toll_plazas.columns)):
    print(f"❌ Error: Missing required columns in toll_plazas.csv! Found: {toll_plazas.columns.tolist()}")
    exit()

# Convert toll plazas into GeoPandas Points
toll_plazas["geometry"] = toll_plazas.apply(lambda row: Point(row["Longitude"], row["Latitude"]), axis=1)
toll_plazas_gdf = gpd.GeoDataFrame(toll_plazas, geometry="geometry", crs="EPSG:4326")

# Extract route coordinates
route_points = [Point(row["Longitude"], row["Latitude"]) for _, row in route_df.iterrows()]

# Define vehicle types and random names
vehicle_types = [
    "Cars and Jeeps", "Minibuses and Tempos", "Two-Axle Trucks",
    "Buses", "Three-Axle Trucks", "Multi-Axle Trucks and Machinery Vehicles"
]
vehicle_names = ["Hyundai Creta", "Tata Nexon", "Toyota Innova", "Scorpio N", "Mahindra XUV700", 
                 "Ashok Leyland Bus", "Volvo Bus", "BharatBenz Truck", "Tata 407", "Eicher Pro"]

# Function to calculate distance (in km) between two points
def calculate_distance(point1, point2):
    return geodesic((point1.y, point1.x), (point2.y, point2.x)).km

# Simulate vehicle movements
num_vehicles = 10000  # Simulate 10,000 vehicle movements
vehicle_data = []

for vehicle_id in range(1, num_vehicles + 1):
    # Select random start plaza
    start_plaza = toll_plazas.sample(n=1).iloc[0]
    start_point = Point(start_plaza["Longitude"], start_plaza["Latitude"])
    
    # Select end location (random toll plaza or full route)
    if random.random() > 0.5:
        destination_plaza = toll_plazas.sample(n=1).iloc[0]
        while destination_plaza["Name"] == start_plaza["Name"]:
            destination_plaza = toll_plazas.sample(n=1).iloc[0]
        destination_point = Point(destination_plaza["Longitude"], destination_plaza["Latitude"])
    else:
        destination_point = route_points[-1]
    
    # Select random vehicle type and name
    vehicle_type = random.choice(vehicle_types)
    vehicle_name = random.choice(vehicle_names)
    
    # Get toll charge per km for the vehicle type
    toll_info = toll_pricing[toll_pricing["Vehicle Type"] == vehicle_type]
    if toll_info.empty:
        continue
    toll_per_km = toll_info["Toll per km (approx.)"].values[0]
    
    # Generate timestamps
    timestamp = datetime.datetime.now() - datetime.timedelta(days=random.randint(0, 30))
    step_duration = datetime.timedelta(minutes=random.randint(5, 15))
    
    # Generate waypoints from start to destination
    vehicle_path = [start_point]
    for _ in range(random.randint(3, 10)):
        random_edge = road_network.sample(n=1).geometry.iloc[0]
        if isinstance(random_edge, LineString):
            random_point = random_edge.interpolate(random.uniform(0, random_edge.length))
            vehicle_path.append(random_point)
    vehicle_path.append(destination_point)
    
    # Store data
    total_distance = 0
    for idx, point in enumerate(vehicle_path):
        if idx == 0:
            distance_from_start = 0
        else:
            distance_from_start = calculate_distance(vehicle_path[0], point)
        
        toll_charge = round(distance_from_start * toll_per_km, 2)
        
        vehicle_data.append([
            vehicle_id, vehicle_name, vehicle_type, timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            point.y, point.x, start_plaza["Name"] if idx == 0 else destination_plaza["Name"] if idx == len(vehicle_path) - 1 else "On Route",
            start_plaza["Name"], round(distance_from_start, 2), toll_charge
        ])
        timestamp += step_duration

# Create DataFrame and save to CSV
df = pd.DataFrame(vehicle_data, columns=[
    "Vehicle_ID", "Vehicle_Name", "Vehicle_Type", "Timestamp", "Latitude", "Longitude",
    "Location", "Start_Location", "Distance_from_Start (km)", "Toll_Charged (INR)"
])
df.to_csv(output_csv_file, index=False)

print(f"📄 Vehicle movement data saved to: {output_csv_file}")
