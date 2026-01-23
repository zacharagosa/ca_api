FROM python:3.11-slim

WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY . .

# Copy frontend build
# We assume frontend/dist exists (built locally or in a previous stage)
# For this simple Dockerfile, we'll copy it from the local context
# In a real CI/CD, we might build it in a multi-stage build
COPY frontend/dist ./frontend/dist

# Expose port
ENV PORT=8080
ENV PYTHONUNBUFFERED=1
EXPOSE 8080

# DEBUG: Verify copy
RUN echo "=== Listing /app ===" && ls -la /app
RUN echo "=== Listing /app/frontend/dist ===" && ls -la /app/frontend/dist

# Run the server
# We will use gunicorn for production
RUN pip install gunicorn
CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 0 server:app
