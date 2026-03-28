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

CLIENT_ID = os.getenv("SENTINEL_CLIENT_ID") # Personal_ID from sentinel-2 website
CLIENT_SECRET = os.getenv("SENTINEL_CLIENT_SECRET") # Personal_Secret from sentinel-2 website
GEMINI_KEY = os.getenv("GEMINI_API_KEY") # Use Own API KEY

client = genai.Client(api_key=GEMINI_KEY)


# PHASE 1: SATELLITE (SENTINEL-2) ENGINE

def get_sentinel_token():
    url = "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token"
    payload = {"client_id": CLIENT_ID, "client_secret": CLIENT_SECRET, "grant_type": "client_credentials"}
    try:
        res = requests.post(url, data=payload, timeout=10)
        return res.json().get("access_token") #A token is required to access the Sentinel-2 API. This function retrieves it using the client credentials provided in the .env file. If the request is successful, it returns the access token; otherwise, it returns None.
    except: return None

def fetch_satellite_metrics(lat, lon):
    token = get_sentinel_token()
    if not token: return None # If the token retrieval fails, the function returns None, indicating that it cannot proceed with fetching satellite data.
    bbox = [lon - 0.005, lat - 0.005, lon + 0.005, lat + 0.005] # The function constructs a bounding box (bbox) around the specified latitude and longitude. This bbox defines the area for which satellite data will be fetched. The bbox is created by adding and subtracting a small value (0.005) from the latitude and longitude to create a square area around the point of interest. Also it equates to 1.21 km squared.
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
    for col in ["sentinel-2-l2a", "sentinel-2-l1c"]: # if one does not works, we have a fallback. L2A is usually preferred for its atmospheric correction, but L1C can be used if L2A data is unavailable or has issues.
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
                    # Formulas for the indices. We also add a check to prevent division by zero, which can happen if the bands have very low values. (these formulas are available in the Sentinel-2 documentation and are standard in remote sensing analysis)
                    "NDVI": round((b08 - b04) / (b08 + b04), 4) if (b08 + b04) != 0 else 0, 
                    "NDWI": round((b03 - b08) / (b03 + b08), 4) if (b03 + b08) != 0 else 0,
                    "NDBI": round((b11 - b08) / (b11 + b08), 4) if (b11 + b08) != 0 else 0,
                    "NDMI": round((b8a - b11) / (b8a + b11), 4) if (b8a + b11) != 0 else 0,
                    "quality": col.upper()
                }
        except: continue
    return None


# PHASE 2: AI API (GEMINI) ENGINE {for comprehensive report and analysis}

def get_ai_analysis(metrics, location):
    # If one model is 503 (Busy), the script will try the next one automatically
    models_to_try = [
        "models/gemini-3-flash-preview", 
        "models/gemini-2.0-flash", 
        "models/gemini-1.5-flash"
    ]
# The prompt is designed to elicit a detailed and structured response from the AI, covering the meanings of the indices, a risk assessment that takes into account the specific challenges faced by the Philippines (like typhoons and urban heat), and actionable recommendations across multiple sectors. The prompt also emphasizes the need for high detail and relevance to the tropical context of the country, ensuring that the AI's analysis is both comprehensive and contextually appropriate.
    prompt = f""" 
    Act as a Chief Urban Sustainability Scientist for the Philippines. 
    Analyze these indices for {location}:
    NDVI: {metrics['NDVI']}, NDWI: {metrics['NDWI']}, NDBI: {metrics['NDBI']}, NDMI: {metrics['NDMI']}.

    Provide a COMPREHENSIVE report in JSON format with:
    1. Data Meanings: Explain what each specific index value indicates for {location}'s environment.
    2. Deep Risk Assessment: Factoring in Philippine realities (typhoons, urban heat, etc.).
    3. Actionable Recommendations: For Urban Planning, Architecture, Engineering, Environmental, Agriculture, and Economics.
    4. Citations: Reference frameworks like UN SDGs or the Philippine Green Building Code (BERDE).
    
    Ensure the response is high-detail and takes into account the specific tropical context of the country.
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
            if "503" in str(e) or "429" in str(e): # Usual errors while using Gemini API Free tier.
                print(f"⚠️  {model_name} is busy or rate-limited. Shifting to next model...")
                time.sleep(2)
                continue
            print(f"❌ Error with {model_name}: {e}")
            continue
    return None

# ---------------------------------------------------------
# EXECUTION
# ---------------------------------------------------------
if __name__ == "__main__":
    print("\n" + "="*60 + "\n🌍 CODINGCUTIES: URBANPLANNER\n" + "="*60)
    loc_name = input("📍 Enter Location: ")
    lat = float(input("🌐 Latitude: "))
    lon = float(input("🌐 Longitude: "))

    print("\n🚀 Starting Pipeline...")
    results = fetch_satellite_metrics(lat, lon)

    if results:
        print(f"✅ Metric Quality: {results['quality']}")
        analysis = get_ai_analysis(results, loc_name)
        if analysis:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M") # This timestamp format ensures that the filename is unique and indicates when the report was generated. It includes the date (year, month, day) and time (hour, minute), which can be helpful for tracking and organizing multiple reports over time.
            filename = f"Analytic_Report_{loc_name.replace(' ', '_')}_{timestamp}.json"
            with open(BASE_DIR / filename, "w") as f:
                json.dump({"metadata": results, "report": analysis}, f, indent=4)
            print(f"\n✅ SUCCESS! saved as: {filename}")
            print("="*60)
        else:
            print("❌ AI analysis failed on all models.")
    else:
        print("❌ Pipeline failed: No satellite data.")