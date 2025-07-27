#!/usr/bin/env python3
"""
FastAPI app for Daily Dewey - returns a different DDC section each day
"""

from fastapi import FastAPI, Query, Response
from fastapi.responses import JSONResponse
from datetime import datetime, timezone, timedelta, date
import hashlib
import os
import sys
from typing import Any
import re

# Add scripts directory to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), "scripts"))

from ddc_helpers import DDCDatabase

app = FastAPI(
    title="Daily Dewey API",
    description="Get a different Dewey Decimal Classification section each day",
    version="1.0.0",
)

# Initialize database
db_path = os.path.join(os.path.dirname(__file__), "ddc_database.db")
ddc_db = DDCDatabase(db_path)


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


@app.get("/")
@app.get("/daily")
async def get_daily_dewey(
    response: Response,
    hint: int | None = Query(None, ge=1, le=3, description="Hint level (1-3)"),
    full: int | None = Query(None, ge=1, le=1, description="Show full information (1)"),
) -> dict[str, Any]:
    """
    Get today's Dewey Decimal Classification section.

    Always returns:
    - date: Today's date
    - main_class: 3-digit main class code (e.g., "600")
    - division: 3-digit division code (e.g., "630")
    - section: 3-digit section code (e.g., "635")

    Query parameters:
    - hint=1: Adds main class description
    - hint=2: Adds main class and division descriptions
    - hint=3: Adds main class, division descriptions, and masked section name
    - full=1: Shows complete information including full section description
    """

    # Get today's section
    section_data = get_daily_section()

    # Build response - always include the three numeric codes
    result: dict[str, Any] = {
        "date": datetime.now(timezone.utc).date().isoformat(),
        "main_class": str(section_data["main_class_code"]).zfill(3),
        "division": str(section_data["division_code"]).zfill(3),
        "section": section_data["section_code"],
    }

    # Add hints progressively
    if hint and hint >= 1:
        result["main_class_description"] = section_data["main_class_description"]

    if hint and hint >= 2:
        result["division_description"] = section_data["division_description"]

    if hint and hint >= 3:
        result["section_masked"] = mask_letters(section_data["section_description"])

    # Show full information if requested
    if full == 1:
        result["section_description"] = section_data["section_description"]
        # Also include all other fields if not already present
        if "main_class_description" not in result:
            result["main_class_description"] = section_data["main_class_description"]
        if "division_description" not in result:
            result["division_description"] = section_data["division_description"]
        if "section_masked" not in result:
            result["section_masked"] = mask_letters(section_data["section_description"])

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
    response.headers["Vary"] = "hint, full"

    return result


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.now(timezone.utc).isoformat()}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
