FROM python:3.12-alpine

# Set working directory
WORKDIR /app

# Install system dependencies (git + build tools if needed)
RUN apk add --no-cache git

# Create a new user `opds` and group
RUN adduser -D opds

# Copy and install dependencies
COPY requirements.txt pytest.ini ./
RUN pip3 install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY database /app/database
COPY opds /app/opds
COPY tests /app/tests


# Give ownership of everything in /app to the opds user
RUN chown -R opds:opds /app

# Switch to the opds user
USER opds

# Set environment variable and run the app
CMD export PYTHONPATH=$(pwd) && python3 opds/main.py
