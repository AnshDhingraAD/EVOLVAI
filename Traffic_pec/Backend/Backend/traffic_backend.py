from fastapi import FastAPI, UploadFile, File
import os
import torch
import numpy as np
from typing import List
from io import BytesIO
from PIL import Image, ImageDraw
import math
import requests
from dotenv import load_dotenv  # Import dotenv to load .env variables
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import base64

# Load environment variables from .env file
load_dotenv()

# Retrieve the API key from the environment variables
API_KEY = os.getenv("API_KEY")

# Initialize FastAPI app
app = FastAPI()

# Add CORSMiddleware to the app
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173/"],  # Allows only the origins specified in the list
    allow_credentials=True,
    allow_methods=["*"],  # Allows all HTTP methods (GET, POST, etc.)
    allow_headers=["*"],  # Allows all headers
)

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
baseDuration = 15  # Minimum green light duration (seconds)
w1 = 0.6  # Weight for queue duration
w2 = 0.4  # Weight for vehicle duration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Update this to restrict origins in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# Function to get AQI based on IP geolocation
def get_aqi_from_ip():
    # Use a geolocation service to get the user's current IP location
    response = requests.get('https://ipinfo.io')
    ip_data = response.json()

    # Get latitude and longitude from the API response
    # location = ip_data.get('loc', '13.0827,80.2707')  # Default to Delhi if not found
    # latitude, longitude = map(float, location.split(','))
    latitude = 13.0477923
    longitude = 80.0734740

    # Now, you can use latitude and longitude to fetch AQI
    return latitude, longitude

# Function to get AQI from OpenWeather API
def get_aqi(latitude, longitude, API_KEY):
    url = f"http://api.openweathermap.org/data/2.5/air_pollution?lat={latitude}&lon={longitude}&appid={API_KEY}"
    response = requests.get(url)
    data = response.json()

    if response.status_code == 200:
        aqi = data["list"][0]["main"]["aqi"]
        return aqi
    else:
        print(f"Error fetching data: {data}")
        return None
    
# Function to calculate the queue duration (based on logarithmic scale)
def calculate_queue_duration(queue_length):
    return k * math.log(queue_length + 1)

# Function to calculate the vehicle type duration
def calculate_vehicle_duration(numCars, numTrucks, numBuses, numBikes):
    return (numCars * carWeight) + (numTrucks * truckWeight) + (numBuses * busWeight) + (numBikes * bikeWeight)

# Function to calculate the AQI impact
def calculate_aqi_impact(aqi):
    """Adjust the green light duration based on AQI."""
    if aqi < 50:
        return 0.8  # Reduce by 20%
    elif 50 <= aqi <= 100:
        return 0.9  # Reduce by 10%
    elif 101 <= aqi <= 200:
        return 1.0  # No change
    elif 201 <= aqi <= 300:
        return 1.2  # Increase by 20%
    else:  # AQI > 300
        return 1.5  # Increase by 50%

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
async def process_images_api(files: List[UploadFile] = File(...)):
    results = []

    # Get the user's current latitude and longitude based on their IP address
    latitude, longitude = get_aqi_from_ip()

    # Get AQI based on latitude and longitude
    aqi = get_aqi(latitude, longitude, API_KEY)
    if aqi is None:
        return {"error": "Failed to fetch AQI data"}

    for file in files:
        # Save the uploaded image to memory (using BytesIO)
        image_data = await file.read()
        image = Image.open(BytesIO(image_data))

        # Detect vehicles in the image
        car_count, truck_count, bike_count = detect_vehicles(image)

        # Calculate queue length (sum of all vehicle counts as an example)
        queue_length = car_count + truck_count + bike_count

        # Calculate green light duration based on vehicle count, AQI, and emergency vehicles
        green_light_duration = calculate_green_light_duration(queue_length, car_count, truck_count, 0, bike_count, aqi, 0)

        # Draw bounding boxes on the image
        image_with_boxes = image.copy()
        results_df = model(np.array(image)).pandas().xyxy[0]
        for index, row in results_df.iterrows():
            x1, y1, x2, y2 = row['xmin'], row['ymin'], row['xmax'], row['ymax']
            cls = int(row['class'])
            if model.names[cls] in ['car', 'truck', 'motorcycle']:  # Only draw boxes for vehicles
                draw = ImageDraw.Draw(image_with_boxes)
                draw.rectangle([x1, y1, x2, y2], outline="red", width=3)

        # Convert the image with bounding boxes to base64
        buffered = BytesIO()
        image_with_boxes.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")

        # Append result for this image
        results.append({
            "image": file.filename,
            "vehicle_count": {
                "cars": car_count,
                "trucks": truck_count,
                "bikes": bike_count
            },
            "green_light_duration": green_light_duration,
            "aqi": aqi,  # Include the AQI in the response
            "image_with_boxes": img_str  # Base64 encoded image with bounding boxes
        })

    return JSONResponse(content={"results": results})

# Start the server
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
