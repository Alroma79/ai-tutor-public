FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY my_agent_bot.py .
COPY chainlit.toml .
COPY chainlit.md .

# Create necessary directories
RUN mkdir -p .files
RUN mkdir -p static

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Expose the port
EXPOSE 8000

# Create a startup script
RUN echo '#!/bin/bash\nset -e\n\necho "Starting Chainlit application..."\nchainlit run my_agent_bot.py --host 0.0.0.0 --port $PORT\n' > /app/start.sh && \
    chmod +x /app/start.sh

# Run the application
CMD ["/app/start.sh"]
