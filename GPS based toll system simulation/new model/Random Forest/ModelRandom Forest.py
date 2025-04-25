import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_squared_error, r2_score
import joblib
import time
import os
from sklearn.impute import SimpleImputer

# Load the dataset
df = pd.read_csv(r"C:\Users\ACER\Downloads\mum_pune_gpsa_data_with_toll.csv")

# Check for columns and ensure no missing data
print("Columns in the dataset:", df.columns)

# Check for missing values
print("Missing values in dataset:")
print(df.isnull().sum())

# Convert 'Timestamp' to datetime
df['Timestamp'] = pd.to_datetime(df['Timestamp'], format='%d-%m-%Y %H:%M', errors='coerce')

# Extract features from the 'Timestamp' column
df['hour'] = df['Timestamp'].dt.hour
df['minute'] = df['Timestamp'].dt.minute
df['second'] = df['Timestamp'].dt.second
df['day'] = df['Timestamp'].dt.day
df['month'] = df['Timestamp'].dt.month
df['year'] = df['Timestamp'].dt.year

# Select relevant features (inputs) and target (output)
base_features = ['hour', 'minute', 'second', 'day', 'month', 'year', 'Longitude', 'Latitude', 'Distance']
target = ['Toll']  # Assuming 'Toll' is the toll fee

# Handle categorical 'Vehicle Type' feature using one-hot encoding
df = pd.get_dummies(df, columns=['Vehicle Type'])

# Update features list to include the one-hot encoded 'Vehicle Type' columns
encoded_vehicle_type_columns = [col for col in df.columns if 'Vehicle Type' in col]
features = base_features + encoded_vehicle_type_columns

# Print the selected features to ensure they are correct
print("Selected Features:", features)

# Handle missing data by imputing only the relevant columns
columns_to_impute = ['Longitude', 'Latitude', 'Distance'] + encoded_vehicle_type_columns

# Impute missing values only for the relevant columns
imputer = SimpleImputer(strategy='mean')  # You can change the strategy to 'median' or 'most_frequent'
df[columns_to_impute] = imputer.fit_transform(df[columns_to_impute])

# Check if there are any missing values left
print("Missing values after imputation:")
print(df.isnull().sum())

# Prepare the input features (X) and target (y)
X = df[features]
y = df[target]

# Split the data into training and testing sets (80% train, 20% test)
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# Initialize Random Forest Regressor model with adjusted parameters
model = RandomForestRegressor(n_estimators=200, max_depth=30, min_samples_split=5, min_samples_leaf=3, max_features='sqrt', random_state=42)

# Measure training time
start_train_time = time.time()
model.fit(X_train, y_train)
end_train_time = time.time()
training_time = end_train_time - start_train_time

# Measure prediction time
start_pred_time = time.time()
predictions = model.predict(X_test)
end_pred_time = time.time()
prediction_time = end_pred_time - start_pred_time

# Calculate Mean Squared Error (MSE) and R^2 score as measures of model performance
mse = mean_squared_error(y_test, predictions)
r2 = r2_score(y_test, predictions)

# Print model evaluation results
print(f"Mean Squared Error: {mse}")
print(f"R^2 Score: {r2}")
print(f"Training Time: {training_time:.4f} seconds")
print(f"Prediction Time: {prediction_time:.4f} seconds")

# Save the trained model to a file
joblib.dump(model, "ModelRandomForest.sav")
print("Model saved as 'ModelRandomForest.sav'")

print("Files saved in:", os.getcwd())
