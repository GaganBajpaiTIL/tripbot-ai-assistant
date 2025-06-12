# command to build and run for dev understanding
# # Build the Docker image
# docker build -t tripbot .
# docker run -it -p50001:50001 --name tripbot"$RANDOM" tripbot
# docker run -it -v $(pwd)/:/app -p50001:50001 --name tripbot"$RANDOM" tripbot
# docker run -it --env-file .env.example -p50001:50001 --name tripbot"$RANDOM" tripbot
# docker exec -it tripbot27037 /bin/bash
# TODO: Set up Terraform for K8 leter. 
# Use Python 3.12 slim as the base image
FROM python:3.12-slim

# Set the working directory in the container
WORKDIR /app

# Install system dependencies required for psycopg2 and other packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY . .

# Copy .env file
COPY .env.example .env

# Install Python dependencies using pip and pyproject.toml
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir .

# Create log directories
RUN mkdir -p /app/log/gunicorn && \
    chown -R nobody:nogroup /app/log/gunicorn

# Expose port 50001
EXPOSE 50001

# Set default environment to development
ENV ENVIRONMENT=development

# Command to run the application with proper config
CMD ["bash", "-c", "echo 'Run in production mode? (Y/N):' && \
    read answer && \
    if [ \"${answer,,}\" = \"y\" ] || [ \"${answer,,}\" = \"yes\" ]; then \
        export ENVIRONMENT=PRODUCTION; \
    else \
        export ENVIRONMENT=development; \
    fi && \
    gunicorn tripbot.app:app --bind 0.0.0.0:50001 --config gunicorn.conf.py"]