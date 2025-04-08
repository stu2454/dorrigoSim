#!/bin/bash

# Check if Docker is installed
if ! command -v docker &> /dev/null
then
    echo "Docker could not be found. Please install Docker first."
    exit 1
fi

# Build the Docker image
echo "Building Docker image..."
docker build -t dorrigo-simulator .

# Run the Docker container
echo "Starting Dorrigo Rural Property Financial Simulator..."
docker run -p 8501:8501 dorrigo-simulator

# The application will be available at http://localhost:8501
echo "Application should now be running at http://localhost:8501"
