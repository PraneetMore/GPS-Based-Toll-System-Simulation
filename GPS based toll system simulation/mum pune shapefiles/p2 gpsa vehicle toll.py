import pandas as pd
from geopy.distance import geodesic
import matplotlib.pyplot as plt
import random

# Read the GPS data with error handling
try:
    gps_df = pd.read_csv("C:/Users/ACER/Downloads/mum_pune_gpsa_data.csv")
except FileNotFoundError:
    print("File not found. Please check the file path.")
    exit()

# Check the columns in the DataFrame
print("Columns in the dataset:", gps_df.columns)

# If 'Vehicle Type' doesn't exist, create it
if 'Vehicle Type' not in gps_df.columns:
    gps_df['Vehicle Type'] = "Cars"  # Default to "Cars" for all rows

# Define vehicle toll rates (updated as per your new values)
vehicle_tolls = {
    "Cars and Jeeps": 3.4,
    "Minibuses and Tempos": 5.3,
    "Two-Axle Trucks": 7.3,
    "Buses": 10,
    "Three-Axle Trucks": 17.3,
    "Multi-Axle Trucks and Machinery Vehicles": 23
}

# Speed in km/h (constant)
speed_kmh = 60
speed_km_per_sec = speed_kmh / 3600  # Convert to km per second

# Function to calculate toll based on vehicle type and distance
def calculate_toll(vehicle_type, distance_km):
    if vehicle_type in vehicle_tolls:
        toll = distance_km * vehicle_tolls[vehicle_type]
        # Apply minimum toll charge
        if toll > 0:
            toll = max(toll, 10)  # Minimum toll of 10 units
        return round(toll, 2)
    else:
        return 0  # No toll for unknown vehicle types

# Calculate distance between consecutive points and store in a new column
gps_df['Distance'] = gps_df.apply(lambda row: geodesic((gps_df.iloc[0]['Latitude'], gps_df.iloc[0]['Longitude']), 
                                                       (row['Latitude'], row['Longitude'])).km, axis=1)

# Filter for distance between 10 km and 97 km
gps_df = gps_df[(gps_df['Distance'] >= 10) & (gps_df['Distance'] <= 97)].reset_index(drop=True)

# Simulate for other vehicles: Randomly assign vehicle types from the defined list
vehicle_types = list(vehicle_tolls.keys())  # All vehicle types from the dictionary
gps_df['Vehicle Type'] = gps_df['Vehicle Type'].apply(lambda x: random.choice(vehicle_types))

# Add calculated toll to the DataFrame
gps_df['Toll'] = gps_df.apply(lambda row: calculate_toll(row['Vehicle Type'], row['Distance']), axis=1)

# Save to new CSV file
output_path = "C:/Users/ACER/Downloads/mum_pune_gpsa_data_with_toll.csv"
gps_df.to_csv(output_path, index=False)
print(f"GPS data with toll fees saved to {output_path}")

# Plot the generated GPS data from the DataFrame
plt.figure(figsize=(10, 6))
for vehicle_type, color in zip(vehicle_types, ['red', 'blue', 'green', 'purple', 'orange', 'black']):
    subset = gps_df[gps_df['Vehicle Type'] == vehicle_type]
    plt.plot(subset['Longitude'], subset['Latitude'], 'o-', color=color, markersize=2, label=vehicle_type)
plt.title("Generated GPS Points for Mumbai-Pune Highway with Tolls (10 km to 97 km)")
plt.xlabel("Longitude")
plt.ylabel("Latitude")
plt.legend()
plt.show()