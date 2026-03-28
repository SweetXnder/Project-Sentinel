import os
import json
import requests
import time
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
from google import genai
from google.genai import types

# 1. SETUP 
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(dotenv_path=BASE_DIR / ".env", override=True)

CLIENT_ID = os.getenv("SENTINEL_CLIENT_ID") 
CLIENT_SECRET = os.getenv("SENTINEL_CLIENT_SECRET") 
GEMINI_KEY = os.getenv("GEMINI_API_KEY") 

client = genai.Client(api_key=GEMINI_KEY)

# ---------------------------------------------------------
# PHASE 1: SATELLITE (SENTINEL-2) ENGINE
# ---------------------------------------------------------

def get_sentinel_token():
    url = "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token"
    payload = {"client_id": CLIENT_ID, "client_secret": CLIENT_SECRET, "grant_type": "client_credentials"}
    try:
        res = requests.post(url, data=payload, timeout=10)
        return res.json().get("access_token") 
    except: return None

def fetch_satellite_metrics(lat, lon):
    token = get_sentinel_token()
    if not token: return None 
    
    bbox = [lon - 0.005, lat - 0.005, lon + 0.005, lat + 0.005] 
    evalscript = """
    //VERSION=3
    function setup() {
        return {
            input: [{bands: ["B02", "B03", "B04", "B08", "B8A", "B11", "dataMask"]}],
            output: [{ id: "default", bands: 6, sampleType: "FLOAT32" }, { id: "dataMask", bands: 1 }]
        };
    }
    function evaluatePixel(sample) {
        return {
            default: [sample.B02, sample.B03, sample.B04, sample.B08, sample.B8A, sample.B11],
            dataMask: [sample.dataMask]
        };
    }
    """
    for col in ["sentinel-2-l2a", "sentinel-2-l1c"]: 
        print(f"📡 Checking {col.upper()}...") 
        payload = {
            "input": {"bounds": {"bbox": bbox}, "data": [{"type": col, "dataFilter": {"maxCloudCoverage": 100}}]},
            "aggregation": {
                "timeRange": {"from": "2025-11-01T00:00:00Z", "to": "2026-03-28T23:59:59Z"},
                "aggregationInterval": {"of": "P130D"},
                "evalscript": evalscript
            }
        }
        try:
            res = requests.post("https://sh.dataspace.copernicus.eu/api/v1/statistics", headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"}, json=payload)
            data = res.json()
            if data.get('data') and len(data['data']) > 0:
                stats = data['data'][0]['outputs']['default']['bands']
                b02, b03, b04, b08, b8a, b11 = stats['B0']['stats']['mean'], stats['B1']['stats']['mean'], stats['B2']['stats']['mean'], stats['B3']['stats']['mean'], stats['B4']['stats']['mean'], stats['B5']['stats']['mean']
                
                return {
                    "NDVI": round((b08 - b04) / (b08 + b04), 4) if (b08 + b04) != 0 else 0, 
                    "NDWI": round((b03 - b08) / (b03 + b08), 4) if (b03 + b08) != 0 else 0,
                    "NDBI": round((b11 - b08) / (b11 + b08), 4) if (b11 + b08) != 0 else 0,
                    "NDMI": round((b8a - b11) / (b8a + b11), 4) if (b8a + b11) != 0 else 0,
                    "raw_bands": {
                        "B02_Blue": round(b02, 5), "B03_Green": round(b03, 5), "B04_Red": round(b04, 5),
                        "B08_NIR": round(b08, 5), "B8A_NarrowNIR": round(b8a, 5), "B11_SWIR": round(b11, 5)
                    },
                    "quality": col.upper(),
                    "coordinates": {"lat": lat, "lon": lon}
                }
        except: continue
    return None


# ---------------------------------------------------------
# PHASE 2: AI API (GEMINI) ENGINE
# ---------------------------------------------------------

def get_ai_analysis(metrics, location):
    models_to_try = ["models/gemini-3-flash-preview", "models/gemini-2.0-flash"]

    prompt = f""" 
    Act as a Chief Urban Sustainability Scientist for the Philippines. 
    Analyze metrics for {location}: {metrics}.

    Provide a JSON report with:
    1. Data Meanings
    2. Deep Risk Assessment
    3. SITE FEASIBILITY ANALYSIS (Solar, Landfills, Parks) within this bbox.
    4. Actionable Recommendations.
    
    RETURN ONLY VALID JSON.
    """

    for model_name in models_to_try:
        try:
            print(f"🔄 Attempting analysis with {model_name}...")
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=types.GenerateContentConfig(response_mime_type="application/json")
            )
            return json.loads(response.text)
        except Exception as e:
            if "429" in str(e) or "503" in str(e):
                print(f"⚠️ {model_name} busy. Waiting 30s...")
                time.sleep(31)
                continue
            print(f"❌ Error with {model_name}: {e}")
            continue
    return None

# ---------------------------------------------------------
# EXECUTION
# ---------------------------------------------------------

if __name__ == "__main__":
    print("\n" + "="*60 + "\n🌍 CODINGCUTIES: DUAL-ENDPOINT SYSTEM\n" + "="*60)
    loc_name = input("📍 Enter Location: ")
    lat = float(input("🌐 Latitude: "))
    lon = float(input("🌐 Longitude: "))

    print("\n🚀 Starting Pipeline...")
    results = fetch_satellite_metrics(lat, lon)

    if results:
        # ENDPOINT 1: RAW METRICS
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        metrics_file = f"Metrics_{loc_name.replace(' ', '_')}_{timestamp}.json"
        with open(BASE_DIR / metrics_file, "w") as f:
            json.dump(results, f, indent=4)
        print(f"✅ Metrics Endpoint Saved: {metrics_file}")

        # ENDPOINT 2: AI ANALYSIS
        analysis = get_ai_analysis(results, loc_name)
        if analysis:
            analysis_file = f"AI_Analysis_{loc_name.replace(' ', '_')}_{timestamp}.json"
            with open(BASE_DIR / analysis_file, "w") as f:
                json.dump(analysis, f, indent=4)
            print(f"✅ AI Analysis Endpoint Saved: {analysis_file}")
            
            print("\n🏗️ FEASIBILITY PREVIEW:")
            sites = analysis.get("SITE FEASIBILITY ANALYSIS", {})
            for project, details in (sites.items() if isinstance(sites, dict) else []):
                print(f"- {project}: {details.get('status', 'N/A')}")
        else:
            print("❌ AI analysis failed.")
    else:
        print("❌ Pipeline failed: No satellite data.")
    print("="*60)