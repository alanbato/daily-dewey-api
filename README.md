# Daily Dewey API

A FastAPI service that returns a different Dewey Decimal Classification (DDC) section each day with progressive hints based on time.

## Overview

This API provides a daily DDC section that changes deterministically each day using MD5 hashing. The same section is returned globally for any given date, with progressive hints revealed throughout the day:

- **Morning (0-8)**: Section code only
- **Mid-day (9-16)**: + Main class description  
- **Late afternoon (17-20)**: + Division description
- **Evening (21-23)**: + Masked section description

## Quick Start

### Using Docker (Recommended)

```bash
# Clone and navigate to directory
cd daily-dewey-api

# Build and run
docker-compose up --build

# API available at http://localhost:8000
```

### Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Build database (if CSV data exists)
python scripts/build_ddc_database.py

# Run server
uvicorn app:app --reload

# API available at http://localhost:8000
```

## API Endpoints

### `GET /daily`

Returns today's DDC section with time-based progressive hints.

**Query Parameters:**
- `hint` (optional): Force hint level (1=main class, 2=division, 3=section)
- `full` (optional): Return all data regardless of time (`full=1`)

**Response:**
```json
{
  "date": "2025-01-15",
  "section": "635",
  "main_class": "600",
  "division": "630", 
  "main_class_description": "Technology",
  "division_description": "Agriculture and related technologies",
  "section_description": "Garden crops (Horticulture)",
  "section_masked": "G_____ c____ (H_____c_____)"
}
```

### `GET /`

Returns API information and available endpoints.

## Database Structure

The DDC database contains:
- **10 main classes** (000-900): Broad subject areas
- **100 divisions** (000-990): More specific topics within each class  
- **1000 sections** (000-999): Detailed subjects within each division

## Project Structure

```
daily-dewey-api/
   app.py                 # FastAPI application
   scripts/
      build_ddc_database.py  # Database creation script
      ddc_sections.csv       # DDC data (1000 sections)
      ddc_helpers.py         # Database query utilities
   data/
      ddc.db                 # SQLite database (generated)
   Dockerfile
   docker-compose.yml
   requirements.txt
   README.md
```

## How It Works

1. **Deterministic Selection**: Uses MD5 hash of current date to select same section globally
2. **Progressive Hints**: Time-based reveal system encourages learning throughout the day
3. **Caching**: Aggressive HTTP caching with `Vary` headers for different query parameters
4. **Complete Coverage**: All 1000 DDC sections can appear over time

## TRMNL Integration

This API is designed to work with the TRMNL e-ink dashboard platform. See the companion TRMNL plugin in `../daily-dewey/` for a complete implementation.

## Development

The database is built from `scripts/ddc_sections.csv` which contains the complete DDC hierarchy. To rebuild:

```bash
python scripts/build_ddc_database.py
```

## License

This project contains data derived from the Dewey Decimal Classification system, which is owned by OCLC.