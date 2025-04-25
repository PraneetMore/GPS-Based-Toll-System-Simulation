import pandas as pd
import numpy as np

# Load the dataset
df = pd.read_csv(r"C:\Users\ACER\Downloads\mum_pune_gpsa_data_with_toll.csv")

# Ensure 'Toll' column exists and check for missing values
if 'Toll' not in df.columns:
    raise ValueError("The dataset does not contain a 'Toll' column.")
if df['Toll'].isnull().any():
    raise ValueError("The 'Toll' column contains missing values. Please clean the dataset.")

# Calculate and print the statistics for the 'Toll' variable
toll_min = df['Toll'].min()
toll_max = df['Toll'].max()
toll_mean = df['Toll'].mean()
toll_std = df['Toll'].std()

print(f"Toll Min: {toll_min}")
print(f"Toll Max: {toll_max}")
print(f"Toll Mean: {toll_mean}")
print(f"Toll Std Dev: {toll_std}")