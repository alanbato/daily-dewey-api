#!/usr/bin/env python3
"""
FastAPI app for Daily Dewey - returns a different DDC section each day
"""

from fastapi import FastAPI, Query, Response, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timezone, timedelta, date
import hashlib
import os
import sys
from typing import Any
import re
import logging
import json
import time

from ddc_helpers import DDCDatabase

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('daily_dewey_api.log')
    ]
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Daily Dewey API",
    description="Get a different Dewey Decimal Classification section each day",
    version="1.0.0",
)

# Add CORS middleware to allow requests from TRMNL platform
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for now
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all HTTP requests and responses"""
    start_time = time.time()
    
    # Log incoming request
    logger.info(f"🔵 INCOMING REQUEST:")
    logger.info(f"   Method: {request.method}")
    logger.info(f"   URL: {request.url}")
    logger.info(f"   Headers: {dict(request.headers)}")
    logger.info(f"   Query params: {dict(request.query_params)}")
    logger.info(f"   Client: {request.client.host if request.client else 'unknown'}")
    
    # Process request
    response = await call_next(request)
    
    # Calculate processing time
    process_time = time.time() - start_time
    
    # Log response
    logger.info(f"🟢 OUTGOING RESPONSE:")
    logger.info(f"   Status: {response.status_code}")
    logger.info(f"   Headers: {dict(response.headers)}")
    logger.info(f"   Processing time: {process_time:.4f}s")
    
    # Add processing time to response headers
    response.headers["X-Process-Time"] = str(process_time)
    
    return response

# Initialize database - check multiple possible locations
db_path = None
possible_paths = [
    os.path.join(os.path.dirname(__file__), "data", "ddc.db"),
    os.path.join(os.path.dirname(__file__), "ddc_database.db"),
    "data/ddc.db",
    "ddc_database.db"
]

for path in possible_paths:
    if os.path.exists(path):
        db_path = path
        break

if not db_path:
    raise FileNotFoundError("Could not find DDC database file")

ddc_db = DDCDatabase(db_path)


@app.on_event("startup")
async def startup_event():
    """Log startup information"""
    logger.info("🚀 Starting Daily Dewey API...")
    logger.info(f"📁 Database path: {db_path}")
    logger.info(f"✅ Database exists: {os.path.exists(db_path)}")
    try:
        test_section = ddc_db.get_section("0")
        logger.info(f"🔍 Database test: {'OK' if test_section else 'No data found'}")
        if test_section:
            logger.info(f"📖 Test section data: {test_section}")
    except Exception as e:
        logger.error(f"❌ Database test error: {e}")
    logger.info("✨ Daily Dewey API ready!")


def get_daily_section() -> dict[str, Any]:
    """Get the DDC section for today based on date"""
    # Use today's date to generate a deterministic "random" section
    today: date = datetime.now(timezone.utc).date()
    date_str = today.isoformat()

    # Create a hash of the date to get a pseudo-random but deterministic number
    hash_object = hashlib.md5(date_str.encode())
    hash_hex = hash_object.hexdigest()
    # Convert first 8 hex chars to int and mod by 1000 to include all sections
    hash_int = int(hash_hex[:8], 16)

    # Get the section for today (including unassigned sections)
    section_code = str(hash_int % 1000)  # All sections 0-999
    section = ddc_db.get_section(section_code)

    if section:
        # Format the section code as a 3-digit decimal number
        section["section_code"] = section_code.zfill(3)
        return section

    # Fallback: get any random section if something goes wrong
    section = ddc_db.get_random_section(exclude_unassigned=False)
    if section:
        # Format the section code as a 3-digit decimal number
        section["section_code"] = str(section["section_code"]).zfill(3)
        return section
    else:
        raise Exception("No Section Found!")


def mask_letters(text: str) -> str:
    """Replace all letters with underscores, preserving spaces and punctuation"""
    return re.sub(r"[a-zA-Z]", "_", text)


@app.get("/daily")
async def get_daily_dewey(
    response: Response,
    hint: int = Query(0, ge=0, le=4, description="Hint level (0-4)"),
) -> dict[str, Any]:
    """
    Get today's Dewey Decimal Classification section.

    Always returns:
    - date: Today's date
    - main_class: 3-digit main class code (e.g., "600")
    - division: 3-digit division code (e.g., "630")
    - section: 3-digit section code (e.g., "635")

    Query parameters:
    - hint=0: Just the numeric codes (default)
    - hint=1: + main class description
    - hint=2: + main class and division descriptions
    - hint=3: + main class, division descriptions, and masked section name
    - hint=4: + complete section description (the answer)
    """
    
    logger.info(f"💡 Processing daily request with hint level: {hint}")

    # Get today's section
    section_data = get_daily_section()
    logger.info(f"📚 Today's section data: {json.dumps(section_data, indent=2)}")

    # Build response - always include the three numeric codes
    result: dict[str, Any] = {
        "date": datetime.now(timezone.utc).date().isoformat(),
        "main_class": str(section_data["main_class_code"]).zfill(3),
        "division": str(section_data["division_code"]).zfill(3),
        "section": section_data["section_code"],
    }
    logger.info(f"🏗️  Base response built: {json.dumps(result, indent=2)}")

    # Add hints progressively based on hint level
    if hint >= 1:
        result["main_class_description"] = section_data["main_class_description"]
        logger.info(f"🔍 Added main class description (hint >= 1)")

    if hint >= 2:
        result["division_description"] = section_data["division_description"]
        logger.info(f"🔍 Added division description (hint >= 2)")

    if hint >= 3:
        result["section_masked"] = mask_letters(section_data["section_description"])
        logger.info(f"🔍 Added masked section (hint >= 3): {result['section_masked']}")

    if hint >= 4:
        result["section_description"] = section_data["section_description"]
        logger.info(f"🔍 Added full section description (hint >= 4)")
    
    logger.info(f"📤 Final response: {json.dumps(result, indent=2)}")

    # Set aggressive caching headers
    # Cache until midnight UTC
    now = datetime.now(timezone.utc)
    midnight = datetime.combine(
        (now + timedelta(days=1)).date(), datetime.min.time()
    ).replace(tzinfo=timezone.utc)
    seconds_until_midnight = int((midnight - now).total_seconds())

    response.headers["Cache-Control"] = (
        f"public, max-age={seconds_until_midnight}, immutable"
    )
    response.headers["Expires"] = midnight.strftime("%a, %d %b %Y %H:%M:%S GMT")
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Vary"] = "hint"

    return result


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Test database connection
        test_section = ddc_db.get_section("0")
        db_status = "connected" if test_section else "no_data"
    except Exception as e:
        db_status = f"error: {str(e)}"
    
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "database": db_status,
        "database_path": db_path
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
