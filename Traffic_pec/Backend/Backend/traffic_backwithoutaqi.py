from fastapi import FastAPI, UploadFile, File
import os
import torch
import numpy as np
from typing import List
from io import BytesIO
from PIL import Image
import math

# Initialize FastAPI app
app = FastAPI()

# Directory to save uploaded images
UPLOAD_DIR = "uploaded_images"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Load YOLOv5 model once (at startup)
model = torch.hub.load('ultralytics/yolov5', 'yolov5s')  # Use YOLOv5 small model for simplicity

# Constants for green light calculation
k = 10  # Scaling factor for queue length
carWeight = 1
truckWeight = 3
busWeight = 2.75
bikeWeight = 0.65
maxGreenDuration = 120  # Maximum green light duration (seconds)
baseDuration = 30  # Minimum green light duration (seconds)
w1 = 0.6  # Weight for queue duration
w2 = 0.4  # Weight for vehicle duration

# Function to calculate the queue duration (based on logarithmic scale)
def calculate_queue_duration(queue_length):
    return k * math.log(queue_length + 1)

# Function to calculate the vehicle type duration
def calculate_vehicle_duration(numCars, numTrucks, numBuses, numBikes):
    return (numCars * carWeight) + (numTrucks * truckWeight) + (numBuses * busWeight) + (numBikes * bikeWeight)

# Function to calculate the AQI impact
def calculate_aqi_impact(aqi):
    return max(1 - (aqi - 100) / 200, 0.5)

# Function to calculate the emergency vehicle impact
def calculate_ev_impact(numEmergencyVehicles):
    return 1 + (numEmergencyVehicles * 0.7)

# Main function to calculate the green light duration
def calculate_green_light_duration(queue_length, numCars, numTrucks, numBuses, numBikes, aqi, numEmergencyVehicles):
    # Step 1: Calculate the queue duration using logarithmic scaling
    queue_duration = calculate_queue_duration(queue_length)

    # Step 2: Calculate the vehicle type duration based on vehicle count
    vehicle_duration = calculate_vehicle_duration(numCars, numTrucks, numBuses, numBikes)

    # Step 3: Calculate the AQI impact (adjustment based on air quality)
    aqi_impact = calculate_aqi_impact(aqi)

    # Step 4: Calculate the emergency vehicle impact
    ev_impact = calculate_ev_impact(numEmergencyVehicles)

    # Step 5: Combine all factors to get the green light duration with weights and limits
    weighted_duration = (w1 * queue_duration + w2 * vehicle_duration) * aqi_impact * ev_impact
    green_light_duration = min(maxGreenDuration, max(baseDuration, weighted_duration))

    return green_light_duration

# Vehicle detection function using YOLOv5
def detect_vehicles(image: Image.Image):
    # Convert the image to numpy array
    image_np = np.array(image)
    
    # Run YOLOv5 inference on the image
    results = model(image_np)

    # Process the results
    df = results.pandas().xyxy[0]  # Extract predictions as a DataFrame

    # Initialize vehicle count
    car_count = 0
    truck_count = 0
    bike_count = 0

    for index, row in df.iterrows():
        cls = int(row['class'])

        # Count vehicles based on class
        if model.names[cls] == 'car':
            car_count += 1
        elif model.names[cls] == 'truck':
            truck_count += 1
        elif model.names[cls] == 'motorcycle':
            bike_count += 1

    return car_count, truck_count, bike_count

# API to process uploaded images and calculate traffic light timings
@app.post("/process_images")
async def process_images_api(files: List[UploadFile] = File(...), aqi: int = 130, numEmergencyVehicles: int = 0):
    results = []

    for file in files:
        # Save the uploaded image to memory (using BytesIO)
        image_data = await file.read()
        image = Image.open(BytesIO(image_data))

        # Detect vehicles in the image
        car_count, truck_count, bike_count = detect_vehicles(image)

        # Calculate queue length (sum of all vehicle counts as an example)
        queue_length = car_count + truck_count + bike_count

        # Calculate green light duration based on vehicle count, AQI, and emergency vehicles
        green_light_duration = calculate_green_light_duration(queue_length, car_count, truck_count, 0, bike_count, aqi, numEmergencyVehicles)

        # Append result for this image
        results.append({
            "image": file.filename,
            "vehicle_count": {
                "cars": car_count,
                "trucks": truck_count,
                "bikes": bike_count
            },
            "green_light_duration": green_light_duration
        })

    return {"results": results}

# Start the server
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
