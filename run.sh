#!/bin/bash

# Load environment variables from .env.example
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
else
    echo "No .env file found. Using .env.example as default."
    export $(cat .env.example | grep -v '^#' | xargs)
fi

# Run the FastAPI app with Uvicorn
uvicorn tripbot.main:app --reload --host 0.0.0.0 --port 50001
