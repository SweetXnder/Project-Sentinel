import os
import json
import time
import requests
from pathlib import Path
from datetime import datetime

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from google import genai
from google.genai import types

# ---------------------------------------------------------------------------
# SETUP
# ---------------------------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(dotenv_path=BASE_DIR / ".env", override=True)

CLIENT_ID     = os.getenv("SENTINEL_CLIENT_ID")
CLIENT_SECRET = os.getenv("SENTINEL_CLIENT_SECRET")
GEMINI_KEY    = os.getenv("GEMINI_API_KEY")

gemini = genai.Client(api_key=GEMINI_KEY)

app = FastAPI(
    title="CodingCuties · UrbanPlanner API",
    description="Satellite-powered urban feasibility analysis for the Philippines.",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# SCHEMAS
# ---------------------------------------------------------------------------

class AnalyzeRequest(BaseModel):
    location: str  = Field(..., example="Quezon City, Metro Manila")
    lat:      float = Field(..., ge=-90,  le=90,  example=14.676)
    lon:      float = Field(..., ge=-180, le=180, example=121.044)

class RawBands(BaseModel):
    B02_blue:       float
    B03_green:      float
    B04_red:        float
    B08_nir:        float
    B8A_narrow_nir: float
    B11_swir:       float

class SatelliteMetrics(BaseModel):
    NDVI:      float
    NDWI:      float
    NDBI:      float
    NDMI:      float
    raw_bands: RawBands
    quality:   str

class AnalyzeResponse(BaseModel):
    location:  str
    lat:       float
    lon:       float
    timestamp: str
    metrics:   SatelliteMetrics
    report:    dict

# ---------------------------------------------------------------------------
# PHASE 1 — SENTINEL-2 SATELLITE ENGINE
# ---------------------------------------------------------------------------

SENTINEL_TOKEN_URL = (
    "https://identity.dataspace.copernicus.eu"
    "/auth/realms/CDSE/protocol/openid-connect/token"
)
SENTINEL_STATS_URL = "https://sh.dataspace.copernicus.eu/api/v1/statistics"

EVALSCRIPT = """
//VERSION=3
function setup() {
    return {
        input:  [{ bands: ["B02","B03","B04","B08","B8A","B11","dataMask"] }],
        output: [
            { id: "default",  bands: 6, sampleType: "FLOAT32" },
            { id: "dataMask", bands: 1 }
        ]
    };
}
function evaluatePixel(sample) {
    return {
        default:  [sample.B02, sample.B03, sample.B04, sample.B08, sample.B8A, sample.B11],
        dataMask: [sample.dataMask]
    };
}
"""

COLLECTIONS = ["sentinel-2-l2a", "sentinel-2-l1c"]   # L2A preferred; L1C is fallback


def _get_token() -> str | None:
    """Fetch a short-lived OAuth2 bearer token from Copernicus."""
    payload = {
        "client_id":     CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "grant_type":    "client_credentials",
    }
    try:
        res = requests.post(SENTINEL_TOKEN_URL, data=payload, timeout=10)
        res.raise_for_status()
        return res.json().get("access_token")
    except Exception:
        return None


def _ndiff(a: float, b: float) -> float:
    """Normalized difference: (a - b) / (a + b), safe against zero division."""
    return round((a - b) / (a + b), 4) if (a + b) != 0 else 0.0


def fetch_satellite_metrics(lat: float, lon: float) -> SatelliteMetrics | None:
    """
    Query the Sentinel-2 Statistics API for a ~1.21 km² box around (lat, lon).
    Returns computed spectral indices or None if no data is available.
    """
    token = _get_token()
    if not token:
        raise HTTPException(status_code=502, detail="Could not authenticate with Sentinel-2.")

    # 0.005° offset ≈ 556 m → bounding box of ~1.21 km²
    bbox = [lon - 0.005, lat - 0.005, lon + 0.005, lat + 0.005]

    for collection in COLLECTIONS:
        payload = {
            "input": {
                "bounds": {"bbox": bbox},
                "data": [{
                    "type":       collection,
                    "dataFilter": {"maxCloudCoverage": 100},
                }],
            },
            "aggregation": {
                "timeRange": {
                    "from": "2025-11-01T00:00:00Z",
                    "to":   "2026-03-28T23:59:59Z",
                },
                "aggregationInterval": {"of": "P130D"},
                "evalscript": EVALSCRIPT,
            },
        }
        try:
            res = requests.post(
                SENTINEL_STATS_URL,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type":  "application/json",
                },
                json=payload,
                timeout=30,
            )
            data = res.json()

            if not (data.get("data") and len(data["data"]) > 0):
                continue

            bands = data["data"][0]["outputs"]["default"]["bands"]
            b02 = bands["B0"]["stats"]["mean"]
            b03 = bands["B1"]["stats"]["mean"]
            b04 = bands["B2"]["stats"]["mean"]
            b08 = bands["B3"]["stats"]["mean"]
            b8a = bands["B4"]["stats"]["mean"]
            b11 = bands["B5"]["stats"]["mean"]

            return SatelliteMetrics(
                NDVI = _ndiff(b08, b04),   # Vegetation density
                NDWI = _ndiff(b03, b08),   # Water content
                NDBI = _ndiff(b11, b08),   # Built-up / urban cover
                NDMI = _ndiff(b8a, b11),   # Vegetation moisture
                raw_bands=RawBands(
                    B02_blue       = round(b02, 5),
                    B03_green      = round(b03, 5),
                    B04_red        = round(b04, 5),
                    B08_nir        = round(b08, 5),
                    B8A_narrow_nir = round(b8a, 5),
                    B11_swir       = round(b11, 5),
                ),
                quality=collection.upper(),
            )

        except Exception:
            continue   # try next collection

    return None

# ---------------------------------------------------------------------------
# PHASE 2 — GEMINI AI ENGINE
# ---------------------------------------------------------------------------

GEMINI_MODELS = ["models/gemini-2.0-flash", "models/gemini-1.5-flash"]


def _build_prompt(metrics: SatelliteMetrics, location: str, lat: float, lon: float) -> str:
    return f"""
Act as a Chief Urban Sustainability Scientist for the Philippines.

Scan Area  : {location}
Coordinates: ({lat}, {lon}) — center of a 1.21 sq km bounding box
Indices    : NDVI={metrics.NDVI}, NDWI={metrics.NDWI}, NDBI={metrics.NDBI}, NDMI={metrics.NDMI}

Produce a COMPREHENSIVE JSON report with EXACTLY these top-level keys:

1. "data_meanings"      — What each index value reveals about this specific area.
2. "risk_assessment"    — Philippine tropical realities: typhoons, urban heat, flooding.
3. "site_feasibility"   — Viability of the following projects WITHIN THIS 1.21 sq km:
     - Solar Panel Arrays      (consider NDBI urban density vs open space)
     - Landfill/Waste Facility (consider NDWI water risk + NDBI proximity)
     - Vertical Greenery/Parks (consider NDBI density vs NDVI deficit)
   Each project must have:
     "status" : one of ["RECOMMENDED", "POSSIBLE WITH MITIGATION", "NOT RECOMMENDED"]
     "reason" : scientific justification referencing the actual index values above.
4. "recommendations"    — Actionable steps for Urban Planning, Architecture,
                          Engineering, Environment, Agriculture, and Economics.
5. "citations"          — Relevant UN SDGs, Philippine BERDE code, or other frameworks.

RETURN ONLY VALID JSON. No markdown, no extra text.
""".strip()


def fetch_ai_analysis(metrics: SatelliteMetrics, location: str, lat: float, lon: float) -> dict:
    """
    Run the satellite metrics through Gemini for a structured feasibility report.
    Tries each model in GEMINI_MODELS before giving up.
    """
    prompt = _build_prompt(metrics, location, lat, lon)

    for model in GEMINI_MODELS:
        try:
            response = gemini.models.generate_content(
                model=model,
                contents=prompt,
                config=types.GenerateContentConfig(response_mime_type="application/json"),
            )
            return json.loads(response.text)

        except Exception as e:
            err = str(e)
            if "429" in err or "503" in err:
                print(f"⚠  {model} busy — retrying in 31 s…")
                time.sleep(31)
                continue
            print(f"✗  {model} error: {e}")
            continue

    raise HTTPException(status_code=503, detail="All Gemini models are currently unavailable.")

# ---------------------------------------------------------------------------
# ROUTES
# ---------------------------------------------------------------------------

@app.get("/health", tags=["Meta"])
def health_check():
    """Simple liveness probe."""
    return {"status": "ok", "service": "UrbanPlanner API", "version": "2.0.0"}


@app.post("/analyze", response_model=AnalyzeResponse, tags=["Analysis"])
def analyze(req: AnalyzeRequest):
    """
    Full pipeline: fetch Sentinel-2 satellite metrics → run Gemini analysis.

    - **location**: Human-readable place name (used in the AI prompt).
    - **lat / lon**: WGS-84 decimal degrees for the center of the scan area.
    """
    metrics = fetch_satellite_metrics(req.lat, req.lon)
    if not metrics:
        raise HTTPException(status_code=404, detail="No satellite data for this location/timeframe.")

    report = fetch_ai_analysis(metrics, req.location, req.lat, req.lon)

    return AnalyzeResponse(
        location  = req.location,
        lat       = req.lat,
        lon       = req.lon,
        timestamp = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        metrics   = metrics,
        report    = report,
    )


@app.post("/analyze/save", tags=["Analysis"])
def analyze_and_save(req: AnalyzeRequest):
    """
    Same as /analyze but also persists the result as a timestamped JSON file
    in the server's working directory.
    """
    result = analyze(req)

    slug      = req.location.replace(" ", "_")
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M")
    filename  = f"Analytic_Report_{slug}_{timestamp}.json"
    filepath  = BASE_DIR / filename

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(result.model_dump(), f, indent=4, ensure_ascii=False)

    return {**result.model_dump(), "saved_to": filename}