FROM python:3.11-slim

WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY app.py .

# Create database directory
RUN mkdir -p data

# Build the database if CSV exists
RUN if [ -f scripts/ddc_sections.csv ]; then python scripts/build_ddc_database.py; fi

# Expose port
EXPOSE 8000

# Run the application
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]