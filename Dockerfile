# Dockerfile

# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set the working directory in the container
WORKDIR /app

# Install dependencies
# Copy the requirements file first to leverage Docker cache
COPY requirements.txt .
RUN python -m pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Expose the port the app runs on
EXPOSE 8000

# Define the command to run the application
# Assumes your Flask app instance is named 'app' in the 'app.py' file
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "app:app"]
