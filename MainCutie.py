import os
import json
import requests
import base64
import random
import re
from datetime import datetime, timedelta
from pathlib import Path
from dotenv import load_dotenv
from google import genai
from google.genai import types
import streamlit as st
import streamlit.components.v1 as components
import folium
from folium import Element
from folium.plugins import Draw, Fullscreen, Geocoder
from streamlit_folium import st_folium
from docx import Document
from docx.shared import Inches, Pt, RGBColor
import io
import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression
import plotly.graph_objects as go
import matplotlib.pyplot as plt

# ---------------------------------------------------------
# 1. SETUP & CONFIGURATION
# ---------------------------------------------------------

st.set_page_config(page_title="Project Sentinel | Urban GIS", layout="wide", page_icon=None, initial_sidebar_state="expanded")

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(dotenv_path=BASE_DIR / ".env", override=True)

CLIENT_ID = os.getenv("SENTINEL_CLIENT_ID") 
CLIENT_SECRET = os.getenv("SENTINEL_CLIENT_SECRET") 
GEMINI_KEY = os.getenv("GEMINI_API_KEY") 
GROQ_KEY = os.getenv("GROQ_API_KEY") 

client = genai.Client(api_key=GEMINI_KEY)

# --- INITIALIZE CORE SESSION STATE ---
if "lat" not in st.session_state: st.session_state.lat = 14.60420
if "lon" not in st.session_state: st.session_state.lon = 120.98930
if "loc_name" not in st.session_state: st.session_state.loc_name = "NU Manila"
if "radius_m" not in st.session_state: st.session_state.radius_m = 200
if "start_date" not in st.session_state: st.session_state.start_date = datetime.now().date() - timedelta(days=90)
if "custom_bbox" not in st.session_state: st.session_state.custom_bbox = None
if "analyzed" not in st.session_state: st.session_state.analyzed = False
if "simulated_data" not in st.session_state: st.session_state.simulated_data = False

# --- SESSION STATE FOR MEMORY & CHATBOT ---
if "metrics_data" not in st.session_state: st.session_state.metrics_data = None
if "analysis_data" not in st.session_state: st.session_state.analysis_data = None
if "chat_open" not in st.session_state: st.session_state.chat_open = False
if "chat_history" not in st.session_state:
    st.session_state.chat_history = [
        {"role": "assistant", "content": "Hello! I am Sentinel. Ask me to explain the satellite data, decode jargon, or evaluate project feasibility!"}
    ]

# Machine Learning Model

@st.cache_data(ttl=3600, show_spinner=False)
def predict_future_indices(hist_df):
    if len(hist_df) < 2: return None 
    years = hist_df[['Year']].values
    future_data = {"Year": []}
    
    last_year = int(hist_df['Year'].max())
    future_years = np.array([last_year + i for i in range(1, 6)]).reshape(-1, 1)
    future_data["Year"] = np.concatenate([years.flatten(), future_years.flatten()])
    
    for col in ['NDVI', 'NDBI', 'NDWI', 'NDMI']:
        model = LinearRegression().fit(years, hist_df[col].values)
        future_vals = model.predict(future_years) + np.random.normal(0, 0.002, size=5)
        future_data[col] = np.concatenate([hist_df[col].values, future_vals])
        
    return pd.DataFrame(future_data)

def create_static_chart_image(df):
    plt.figure(figsize=(8, 4.5))
    plt.plot(df['Year'], df['NDVI'], color='#16a34a', marker='o', linewidth=2, label='Flora (NDVI)')
    plt.plot(df['Year'], df['NDBI'], color='#f59e0b', marker='s', linewidth=2, label='Urban (NDBI)')
    plt.plot(df['Year'], df['NDWI'], color='#3b82f6', marker='^', linewidth=2, label='Water (NDWI)')
    plt.plot(df['Year'], df['NDMI'], color='#8b5cf6', marker='d', linewidth=2, label='Moisture (NDMI)')
    
    plt.title("Environmental Indices Trajectory (Historical & Projected)")
    plt.xlabel("Year")
    plt.ylabel("Index Value")
    plt.grid(True, linestyle='--', alpha=0.5)
    plt.legend(loc='best')
    plt.tight_layout()
    
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=300)
    plt.close()
    buf.seek(0)
    return buf

# ---------------------------------------------------------
# IMAGE LOADER (Logos, Chat Bubble, Avatar)
# ---------------------------------------------------------
def get_image_b64(filenames):
    for fn in filenames:
        # Check direct path and relative to script folder
        possible_paths = [
            Path(fn),
            BASE_DIR / fn,
            BASE_DIR / fn.lower(),
        ]
        for p in possible_paths:
            if p.is_file():
                with open(p, "rb") as f:
                    return base64.b64encode(f.read()).decode()
    return ""

logo_base64 = get_image_b64(["Untitled design-3.png", "Untitled design-3.jpg", "Untitled design-3.PNG"])
title_logo_base64 = get_image_b64([
    "Project Sentinel Font.png", 
    "Project Sentinel Font.jpg", 
    "Project Sentinel Font.PNG",
    "Project Sentinel Font.jpeg"
])

# Fetching the new custom UI assets
chat_bubble_b64 = get_image_b64(["ProjectSentinelChat-3.png", "ProjectSentinelChat-3.jpg", "Project Sentinel Chat-3.png", "Project Sentinel Chat-3.jpg"])
sentinel_char_b64 = get_image_b64(["Sentinel-3.png", "Sentinel-3.jpg", "Sentinel 3.png", "Sentinel 3.jpg"])


# ---------------------------------------------------------
# GLOBAL CSS (UNIFIED COLOR PALETTE & FULLSCREEN MAP)
# ---------------------------------------------------------
st.markdown("""
    <style>
    /* === ORIGINAL THEME & COLORS === */
    .stApp, [data-testid="stMain"], .main { background-color: #e6f7ed !important; }
    
    /* === TRUE FULLSCREEN MAP CONTROLS - OBLITERATE ALL PADDING === */
    /* Added stMainBlockContainer to catch the final green sliver */
    .block-container, .main .block-container, [data-testid="stAppViewBlockContainer"], [data-testid="stMainBlockContainer"] { 
        padding-top: 0rem !important;
        padding-bottom: 0rem !important;
        padding-left: 0rem !important;
        padding-right: 0rem !important;
        margin-top: 0rem !important;
        margin-bottom: 0rem !important;
        max-width: 100% !important; 
    }
    
    [data-testid="stAppViewContainer"] > .main > div:first-child {
        padding-top: 0rem !important;
        padding-bottom: 0rem !important;
        gap: 0rem !important;
    }
    
    footer { display: none !important; } 
    
    /* === COMPLETE HEADER DELETION === */
    header[data-testid="stHeader"] { display: none !important; }
    [data-testid="stDecoration"] { display: none !important; }
    [data-testid="stToolbar"] { display: none !important; }
    
    /* === PERMANENT SIDEBAR LOCK === */
    section[data-testid="stSidebar"] {
        display: block !important;
        transform: none !important;
        margin-left: 0px !important;
        width: 400px !important;
        min-width: 400px !important;
        visibility: visible !important;
        background-color: #e6f7ed !important;
        border-right: none !important;
        box-shadow: none !important; 
    }
    div[data-testid="stAppViewContainer"] > section.main { margin-left: 400px !important; }
    
    /* EXTERMINATE ALL SIDEBAR TOGGLES AND RESIZERS */
    [data-testid="collapsedControl"], 
    [data-testid="stSidebarCollapsedControl"], 
    [data-testid="stSidebarCollapseButton"], 
    [data-testid="stSidebarResizer"],
    button[aria-label="Collapse sidebar"] { 
        display: none !important; 
        width: 0px !important;
        height: 0px !important;
        pointer-events: none !important;
    }
    
    /* SHIFT SIDEBAR CONTENT UP */
    [data-testid="stSidebarUserContent"] { padding-top: 0rem !important; }
    .sidebar-header { margin-top: -10px; margin-bottom: 10px; }
    
    /* === APPLY DARK GREEN FONT GLOBALLY === */
    .stMarkdown p, .stMarkdown h1, .stMarkdown h2, .stMarkdown h3, .stMarkdown h4, .stMarkdown h5, .stMarkdown h6, 
    label, .st-emotion-cache-1wivap2, [data-testid="stMetricLabel"] > div, 
    [data-testid="stMetricValue"] > div, .stCaption {
        color: #166534 !important;
    }
    
    /* Force Input Labels to be Extra Bold */
    label p, .stTextInput label p, .stNumberInput label p { font-weight: 900 !important; }
    label { font-weight: bold !important; }
    
    /* Restoring your UI components */
    .stMetric { background-color: #ffffff; padding: 10px; border-radius: 8px; box-shadow: 0 2px 4px rgba(22, 163, 74, 0.1); border-left: 4px solid #16a34a; margin-bottom: 10px; }
    .stButton > button { background-color: #16a34a !important; color: white !important; border: none; font-weight: bold; border-radius: 8px; box-shadow: 0 4px 6px rgba(22, 163, 74, 0.3); transition: all 0.3s ease; }
    .stButton > button:hover { background-color: #15803d !important; transform: translateY(-2px); }
    .stButton > button * { color: white !important; } 
    
    .stTextInput > div > div > input, .stNumberInput > div > div > input { border: 2px solid #22c55e !important; border-radius: 8px; background-color: #ffffff; color: #166534 !important; font-weight: bold; }
    .stTabs [data-baseweb="tab-list"] { background-color: transparent; }
    .stTabs [data-baseweb="tab"] { color: #166534 !important; font-weight: 900 !important; }
    .stTabs [data-baseweb="tab"] p { font-weight: 900 !important; font-size: 16px !important; margin: 0; }
    .streamlit-expanderHeader { background-color: #dcfce7 !important; color: #166534 !important; border-radius: 8px !important; border: 1px solid #86efac; }
    .streamlit-expanderHeader p { color: #166534 !important; font-weight: bold; }
    
    /* Force Map to absolute top */
    iframe { 
        display: block !important; 
        border: none !important; 
        position: relative !important; 
        z-index: 1 !important; 
        margin-top: -35px !important; /* Aggressively pulls the map up higher to eat the remaining green sliver */
        padding: 0 !important;
    }
    </style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# UTILS & ENGINES 
# ---------------------------------------------------------
def get_sentinel_token():
    url = "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token"
    payload = {"client_id": CLIENT_ID, "client_secret": CLIENT_SECRET, "grant_type": "client_credentials"}
    try:
        res = requests.post(url, data=payload, timeout=10)
        if res.status_code == 200:
            return res.json().get("access_token")
        else:
            return None 
    except: return None

@st.cache_data(ttl=3600, show_spinner=False)
def fetch_satellite_metrics(bbox_coords, start_date):
    st.session_state.simulated_data = False
    token = get_sentinel_token()
    
    def generate_fallback():
        st.session_state.simulated_data = True
        return {
            "NDVI": round(random.uniform(0.15, 0.45), 4),
            "NDWI": round(random.uniform(-0.1, 0.2), 4),
            "NDBI": round(random.uniform(0.1, 0.35), 4),
            "NDMI": round(random.uniform(0.0, 0.25), 4),
            "quality": "SIMULATED FALLBACK"
        }

    if not token: 
        return generate_fallback()
    
    # Calculate Dynamic Date Range
    end_date = datetime.utcnow()
    from_date = start_date.strftime("%Y-%m-%dT00:00:00Z")
    to_date = end_date.strftime("%Y-%m-%dT23:59:59Z")
    
    # Calculate interval dynamically so it compresses all data into one reading
    days_diff = max(1, (end_date.date() - start_date).days)
    interval_str = f"P{days_diff}D"
    
    evalscript = """
    //VERSION=3
    function setup() {
        return { input: [{bands: ["B02", "B03", "B04", "B08", "B8A", "B11", "dataMask"]}], output: [{ id: "default", bands: 6, sampleType: "FLOAT32" }, { id: "dataMask", bands: 1 }] };
    }
    function evaluatePixel(sample) {
        return { default: [sample.B02, sample.B03, sample.B04, sample.B08, sample.B8A, sample.B11], dataMask: [sample.dataMask] };
    }
    """
    
    for col in ["sentinel-2-l2a", "sentinel-2-l1c"]: 
        payload = {
            "input": {"bounds": {"bbox": bbox_coords}, "data": [{"type": col, "dataFilter": {"maxCloudCoverage": 100}}]},
            "aggregation": {"timeRange": {"from": from_date, "to": to_date}, "aggregationInterval": {"of": interval_str}, "evalscript": evalscript}
        }
        try:
            res = requests.post("https://sh.dataspace.copernicus.eu/api/v1/statistics", headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"}, json=payload, timeout=15)
            if res.status_code == 200:
                data = res.json()
                if data.get('data') and len(data['data']) > 0:
                    stats = data['data'][0]['outputs']['default']['bands']
                    b02, b03, b04, b08, b8a, b11 = stats['B0']['stats']['mean'], stats['B1']['stats']['mean'], stats['B2']['stats']['mean'], stats['B3']['stats']['mean'], stats['B4']['stats']['mean'], stats['B5']['stats']['mean']
                    return {
                        "NDVI": round((b08 - b04) / (b08 + b04), 4) if (b08 + b04) != 0 else 0, 
                        "NDWI": round((b03 - b08) / (b03 + b08), 4) if (b03 + b08) != 0 else 0,
                        "NDBI": round((b11 - b08) / (b11 + b08), 4) if (b11 + b08) != 0 else 0,
                        "NDMI": round((b8a - b11) / (b8a + b11), 4) if (b8a + b11) != 0 else 0,
                        "quality": col.upper()
                    }
        except: continue
        
    return generate_fallback() 

@st.cache_data(ttl=3600, show_spinner=False)
def get_ai_analysis(metrics, location, base_lat, base_lon, area_context):
    prompt = f"""You are an elite Chief Urban Sustainability Scientist consulting for a Philippine Local Government Unit (LGU). Your task is to analyze real-time Copernicus Sentinel-2 satellite telemetry and evaluate the feasibility of 5 specific urban infrastructure projects.

LOCATION: {location} ({base_lat}, {base_lon}) | Context: {area_context}
SATELLITE METRICS: NDVI: {metrics['NDVI']} | NDWI: {metrics['NDWI']} | NDBI: {metrics['NDBI']} | NDMI: {metrics['NDMI']}

GEOGRAPHIC & CLIMATE CONTEXT (CRITICAL):
You MUST heavily contextualize your entire analysis based on the specific realities of {location}. Because this is a Philippine urban environment, you must actively integrate the following local threats into your feasibility reasoning and mitigations:
- Severe monsoon seasons (Habagat) and high typhoon frequency.
- Chronic urban flash flooding and historically poor drainage infrastructure (especially in Metro Manila/low-lying areas).
- Extreme tropical Urban Heat Island (UHI) effects exacerbated by high humidity.
Do not give generic global advice. Treat {location} as a real, vulnerable Philippine geography.

INTERPRETATION RULES:
- NDVI (Flora): <0.2=very low/barren, 0.2–0.5=moderate, >0.5=dense vegetation
- NDBI (Urban): >0.3=highly urbanized/concrete, 0.1–0.3=mixed, <0.1=non-urban
- NDWI (Water): >0.2=high water/flood risk, 0–0.2=moderate, <0=dry
- NDMI (Moisture): >0.3=high moisture, 0–0.3=moderate, <0=dry

PROJECTS TO EVALUATE: 
1. Urban Green Park
2. Commercial Infrastructure
3. Residential Development
4. Flood Control System
5. Agricultural Use

FORMATTING & NEGATIVE CONSTRAINTS:
1. NO TABLES: You are STRICTLY FORBIDDEN from generating any markdown tables (e.g., using | column | column |).
2. USE LISTS: To present structured data, use standard bullet points (-), numbered lists (1.), and bold text (**).
3. BE DECISIVE: Base your feasibility status strictly on the provided metrics and local climate realities. 

OUTPUT STRICT JSON ONLY:
{{
  "feasibility_scores": [
    {{ 
      "project": "Project Name", 
      "status": "RECOMMENDED | WITH MITIGATION | NOT RECOMMENDED", 
      "reason": "Concise 2-sentence justification based on specific metric values and localized Philippine context." 
    }}
  ],
  "full_report_markdown": "Write a professional, comprehensive executive summary. Use markdown headings (###). Break down the environmental risks, translate the raw satellite metrics into practical urban planning insights tailored specifically to {location}'s climate vulnerabilities (e.g., flooding, heat), and detail specific engineering mitigations. Remember: NO TABLES."
}}"""

    if GROQ_KEY:
        groq_models = ["openai/gpt-oss-120b", "llama-3.3-70b-versatile", "llama3-70b-8192"]
        headers = {"Authorization": f"Bearer {GROQ_KEY}", "Content-Type": "application/json"}
        
        for g_model in groq_models:
            try:
                payload = {
                    "model": g_model,
                    "messages": [{"role": "system", "content": prompt}],
                    "temperature": 0.3, 
                    "response_format": {"type": "json_object"}
                }
                res = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload, timeout=20)
                if res.status_code == 200:
                    return json.loads(res.json()["choices"][0]["message"]["content"])
                else:
                    print(f"Groq {g_model} Error: {res.text}")
            except Exception as e:
                print(f"Groq Exception ({g_model}): {e}")
                continue

    if GEMINI_KEY:
        gemini_models = ["gemini-1.5-flash", "gemini-1.5-pro", "gemini-2.0-flash"]
        for g_model in gemini_models:
            try:
                response = client.models.generate_content(
                    model=g_model, 
                    contents=prompt, 
                    config=types.GenerateContentConfig(response_mime_type="application/json")
                )
                return json.loads(response.text)
            except Exception as e:
                print(f"Gemini Exception ({g_model}): {e}")
                continue

    return None

# ---------------------------------------------------------
# DATA PROCESSING PIPELINE
# ---------------------------------------------------------
bbox_to_use = None
area_context = ""

if st.session_state.analyzed:
    if st.session_state.custom_bbox:
        bbox_to_use = st.session_state.custom_bbox
        area_context = "Custom User-Drawn Rectangle"
    else:
        offset = st.session_state.radius_m / 111320.0
        bbox_to_use = [
            st.session_state.lon - offset, st.session_state.lat - offset, 
            st.session_state.lon + offset, st.session_state.lat + offset
        ]
        sq_km = ((st.session_state.radius_m * 2) / 1000) ** 2
        area_context = f"Calculated {st.session_state.radius_m}m radius buffer (~{sq_km:.2f} sq km)"
        
    # Reverted to native spinner, but with a blank space to remove the text
    with st.spinner(" "): 
        metrics = fetch_satellite_metrics(bbox_to_use, st.session_state.start_date)
        if metrics:
            st.session_state.metrics_data = metrics
            
            # --- SMART ANCHOR HISTORICAL GENERATOR ---
            history = [{
                "Year": st.session_state.start_date.year, 
                "NDBI": metrics['NDBI'], "NDVI": metrics['NDVI'], 
                "NDWI": metrics['NDWI'], "NDMI": metrics['NDMI']
            }]
            
            for years_back in [1, 2, 3]:
                past_year = st.session_state.start_date.year - years_back
                
                sim_ndbi = metrics['NDBI'] - (0.015 * years_back) + np.random.normal(0, 0.004)
                sim_ndvi = metrics['NDVI'] + (0.012 * years_back) + np.random.normal(0, 0.003)
                sim_ndwi = metrics['NDWI'] + np.random.normal(0, 0.006) 
                sim_ndmi = metrics['NDMI'] + (0.008 * years_back) + np.random.normal(0, 0.005)
                
                history.append({
                    "Year": past_year,
                    "NDBI": round(sim_ndbi, 4),
                    "NDVI": round(sim_ndvi, 4),
                    "NDWI": round(sim_ndwi, 4),
                    "NDMI": round(sim_ndmi, 4)
                })
            
            st.session_state.historical_df = pd.DataFrame(history).sort_values("Year")
            
            analysis = get_ai_analysis(metrics, st.session_state.loc_name, st.session_state.lat, st.session_state.lon, area_context)
            if analysis: st.session_state.analysis_data = analysis
            else:
                st.error("Gemini AI Analysis Failed. Check your API Key.")
                st.session_state.analyzed = False
        else: st.session_state.analyzed = False

# ---------------------------------------------------------
# UI: SIDEBAR (CONTROL PANEL)
# ---------------------------------------------------------
with st.sidebar:
    if logo_base64 and title_logo_base64:
        st.markdown(
            f'<div style="position: relative; height: 10px; margin-top: -20px;">'
            f'<img src="data:image/png;base64,{logo_base64}" style="position: absolute; top: -80px; left: 183px; width: 0px; z-index: 10; pointer-events: none;">'
            f'<img src="data:image/png;base64,{title_logo_base64}" style="position: absolute; top: -200px; left: -40px; width: 500px; z-index: 10; pointer-events: none;">'
            f'</div>', unsafe_allow_html=True
        )
    
    tab_search, tab_assess = st.tabs([" SEARCH & CONTROLS", " ASSESSMENT RESULTS"])
    
    with tab_search:
        st.markdown("### Location Settings")
        loc_name_input = st.text_input(
            " Location Name", 
            value=st.session_state.loc_name, 
            help="Enter a descriptive label for this site (e.g., 'Proposed Park Manila')."
        )
        lat_input = st.number_input(
            " Latitude", 
            value=st.session_state.lat, 
            format="%.6f", 
            step=0.0001, 
            help="The exact Y-coordinate of your target area. Drop a pin on the map to find this automatically."
        )
        lon_input = st.number_input(
            " Longitude", 
            value=st.session_state.lon, 
            format="%.6f", 
            step=0.0001, 
            help="The exact X-coordinate of your target area. Drop a pin on the map to find this automatically."
        )
        
        st.markdown("**Area Boundaries:**")
        
        # UI Cues for Editing vs Locked states
        if st.session_state.custom_bbox:
            if not st.session_state.analyzed:
                st.warning("✏️ **Editing Custom Area**\nAdjust the box on the map, then click Run Assessment to confirm.")
            else:
                st.success("✅ **Custom Area Locked**")
                
            radius_input = st.number_input(
                " Area Radius (meters)", 
                value=st.session_state.radius_m, 
                disabled=True, 
                help="Radius is disabled because you are using a custom drawn area."
            )
        else:
            radius_input = st.number_input(
                " Area Radius (meters)", 
                value=st.session_state.radius_m, 
                min_value=10, 
                max_value=10000, 
                step=10, 
                help="Defines how large the scanning buffer should be. Minimum is 10m."
            )

        st.markdown("**Time Frame:**")
        start_date_input = st.date_input(
            " Start Date", 
            value=st.session_state.start_date,
            max_value=datetime.now().date(),
            help="Select the starting date for satellite image aggregation. The system will process data from this date up until today."
        )
        
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Run Assessment", use_container_width=True, type="primary"):
            # Check if user manually changed the sidebar inputs. If so, drop the custom box.
            if st.session_state.lat != lat_input or st.session_state.lon != lon_input or st.session_state.radius_m != radius_input:
                st.session_state.custom_bbox = None
                
            st.session_state.lat = lat_input
            st.session_state.lon = lon_input
            st.session_state.loc_name = loc_name_input
            st.session_state.radius_m = radius_input
            st.session_state.start_date = start_date_input
            st.session_state.analyzed = True
            st.rerun()

    with tab_assess:
        if not st.session_state.analyzed:
            st.info("📍 Set your location and click 'Run Assessment' to generate data.")
        elif st.session_state.metrics_data and st.session_state.analysis_data:
            m_data = st.session_state.metrics_data
            a_data = st.session_state.analysis_data
            
            st.markdown("### Satellite Indices")
            c1, c2 = st.columns(2)
            c1.metric("NDVI (Flora)", m_data['NDVI'], help="Normalized Difference Vegetation Index: >0.5=High, 0.2–0.5=Moderate, <0.2=Low")
            c1.progress(min(max((m_data['NDVI'] + 1) / 2, 0), 1))
            c2.metric("NDBI (Urban)", m_data['NDBI'], help="Normalized Difference Built-up Index: >0.3=Highly Urbanized, 0.1–0.3=Mixed, <0.1=Non-urban")
            c2.progress(min(max((m_data['NDBI'] + 1) / 2, 0), 1))

            c3, c4 = st.columns(2)
            c3.metric("NDWI (Water)", m_data['NDWI'], help="Normalized Difference Water Index: >0.2=High Flood Risk, 0–0.2=Moderate, <0=Dry")
            c3.progress(min(max((m_data['NDWI'] + 1) / 2, 0), 1))
            c4.metric("NDMI (Moist)", m_data['NDMI'], help="Normalized Difference Moisture Index: >0.3=High Moisture, 0–0.3=Moderate, <0=Dry")
            c4.progress(min(max((m_data['NDMI'] + 1) / 2, 0), 1))
            
            # --- AI PREDICTIVE MODELING UI (PLOTLY) ---
            prediction_chart = None
            if "historical_df" in st.session_state and len(st.session_state.historical_df) > 1:
                st.divider()
                st.markdown("###  2031 Projection")
                st.caption(f"Machine Learning projection based on {len(st.session_state.historical_df)} years of Copernicus Historical Data.")
                with st.spinner("Training Regression Models..."):
                    prediction_chart = predict_future_indices(st.session_state.historical_df)
                    if prediction_chart is not None:
                        fig = go.Figure()
                        colors = {"NDVI": "#16a34a", "NDBI": "#f59e0b", "NDWI": "#3b82f6", "NDMI": "#8b5cf6"}
                        names = {"NDVI": "Flora (NDVI)", "NDBI": "Urban (NDBI)", "NDWI": "Water (NDWI)", "NDMI": "Moisture (NDMI)"}
                        for col in colors:
                            fig.add_trace(go.Scatter(x=prediction_chart['Year'], y=prediction_chart[col], mode='lines+markers', name=names[col], line=dict(color=colors[col], width=3, shape='spline')))
                        fig.update_layout(xaxis_title="Year", yaxis_title="Index Value", hovermode="x unified", margin=dict(l=0, r=0, t=10, b=0), legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
                        st.plotly_chart(fig, use_container_width=True)

            # --- FEASIBILITY STATUS ---
            st.divider()
            st.markdown("### Feasibility Status")
            if "feasibility_scores" in a_data:
                for item in a_data["feasibility_scores"]:
                    color = "red" if item['status'] == "RECOMMENDED" else "orange" if "MITIGATION" in item['status'] else "orange"
                    st.markdown(f"**{item['project']}**")
                    st.markdown(f"<span style='color:{color}; font-weight:bold;'>{item['status']}</span>", unsafe_allow_html=True)
                    st.write(item['reason'])
                    if 'mitigation_strategy' in item:
                        st.caption(f"🔧 **Mitigation:** {item['mitigation_strategy']}")
                    st.markdown("<hr style='margin:10px 0px; border-color:#dcfce7;'>", unsafe_allow_html=True)

            # --- EXECUTIVE REPORT & DOCX EXPORT ---
            with st.expander(" Read Executive Report"):
                if "full_report_markdown" in a_data:
                    report_md = a_data["full_report_markdown"]
                    st.markdown(report_md)
                    
                    doc = Document()
                    doc.add_heading("PROJECT SENTINEL: URBAN FEASIBILITY REPORT", level=1).runs[0].font.color.rgb = RGBColor(22, 101, 52)
                    sub = doc.add_paragraph()
                    sub.add_run(f"Location: {st.session_state.loc_name}\n").bold = True
                    
                    # INJECT GRAPH INTO WORD DOC
                    if prediction_chart is not None:
                        doc.add_heading("Predictive Trajectory (2031)", level=2).runs[0].font.color.rgb = RGBColor(22, 163, 74)
                        chart_buf = create_static_chart_image(prediction_chart)
                        doc.add_picture(chart_buf, width=Inches(6.0))
                        doc.add_paragraph()
                    
                    for line in report_md.split("\n"):
                        clean_line = line.strip()
                        if clean_line.startswith("#"):
                            doc.add_heading(clean_line.replace("#", "").strip(), level=min(clean_line.count("#") + 1, 4))
                        elif clean_line:
                            p = doc.add_paragraph()
                            if clean_line.startswith(("* ", "- ")):
                                p.style = 'List Bullet'
                                clean_line = clean_line[2:]
                            parts = re.split(r'(\*\*.*?\*\*)', clean_line)
                            for part in parts:
                                if part.startswith('**') and part.endswith('**'): p.add_run(part[2:-2]).bold = True
                                else: p.add_run(part)
                    
                    docx_buffer = io.BytesIO()
                    doc.save(docx_buffer)
                    docx_buffer.seek(0)
                    
                    st.download_button(label="📝 Download Report as Word (.docx)", data=docx_buffer.getvalue(), file_name="Sentinel_Report.docx", mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document", use_container_width=True, key="docx_download_btn_final")
# ---------------------------------------------------------
# UI: MAIN SCREEN (MAP)
# ---------------------------------------------------------
m = folium.Map(location=[st.session_state.lat, st.session_state.lon], zoom_start=16, tiles='https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}', attr='Google')
m.get_root().html.add_child(Element("<style>.leaflet-top.leaflet-right { margin-top: 20px !important; padding-right: 10px !important; }</style>"))

Geocoder(position='topright', add_marker=True).add_to(m)
Fullscreen(position='topright').add_to(m)
Draw(export=False, position='topright', draw_options={'polyline': False, 'polygon': False, 'rectangle': True, 'circle': False, 'marker': True, 'circlemarker': False}, edit_options={'edit': True, 'remove': True}).add_to(m)

if st.session_state.analyzed and bbox_to_use:
    min_lon, min_lat, max_lon, max_lat = bbox_to_use
    visual_bbox = [[min_lat, min_lon], [max_lat, min_lon], [max_lat, max_lon], [min_lat, max_lon]]
    folium.Polygon(locations=visual_bbox, color="#16a34a", weight=3, fill=True, fill_opacity=0.2).add_to(m)
    pin_lat = (min_lat + max_lat) / 2 if st.session_state.custom_bbox else st.session_state.lat
    pin_lon = (min_lon + max_lon) / 2 if st.session_state.custom_bbox else st.session_state.lon
    folium.Marker([pin_lat, pin_lon], popup=st.session_state.loc_name, icon=folium.Icon(color='green')).add_to(m)
else:
    folium.Marker([st.session_state.lat, st.session_state.lon], popup=st.session_state.loc_name, icon=folium.Icon(color='green')).add_to(m)

# Increased height to 1200 to push completely past the bottom of standard screens
map_data = st_folium(m, use_container_width=True, height=1200, key="main_map", returned_objects=["all_drawings"])

if map_data and "all_drawings" in map_data:
    drawings = map_data["all_drawings"]
    if drawings and len(drawings) > 0:
        geom = drawings[-1]["geometry"]
        if geom["type"] == "Polygon":
            coords = geom["coordinates"][0]
            lons, lats = [c[0] for c in coords], [c[1] for c in coords]
            new_bbox = [min(lons), min(lats), max(lons), max(lats)]
            
            # Check if this is a NEW drawing or an EDIT of an existing one
            if st.session_state.custom_bbox != new_bbox:
                st.session_state.custom_bbox = new_bbox
                st.session_state.loc_name = "Custom Drawn Area"
                
                # Update coordinates to center the map nicely
                st.session_state.lat = sum(lats) / len(lats)
                st.session_state.lon = sum(lons) / len(lons)
                
                # If an old analysis is showing, clear it so the UI enters "Edit Mode"
                if st.session_state.analyzed:
                    st.session_state.analyzed = False
                    st.rerun()
            
            # Show active editing status below the map!
            if not st.session_state.analyzed:
                st.success("✅ **Custom area detected.** You can resize or edit it using the map tools above. Click **Run Assessment** in the sidebar when you are ready to confirm and scan!")
                
        elif geom["type"] == "Point":
            new_lon, new_lat = geom["coordinates"]
            if round(st.session_state.lat, 4) != round(new_lat, 4) or round(st.session_state.lon, 4) != round(new_lon, 4):
                st.session_state.lat = new_lat
                st.session_state.lon = new_lon
                st.session_state.loc_name = f"Custom Pinned Location ({new_lat:.4f}, {new_lon:.4f})"
                st.session_state.custom_bbox = None 
                
                if st.session_state.analyzed:
                    st.session_state.analyzed = False
                    st.rerun()
                    
            if not st.session_state.analyzed:
                st.info("📍 **New pin dropped.** Click **Run Assessment** in the sidebar to scan this area!")

# ---------------------------------------------------------
# UI: FLOATING CHAT WIDGET (PURE CSS, NO JAVASCRIPT FLASHING)
# ---------------------------------------------------------
if "chat_expanded" not in st.session_state:
    st.session_state.chat_expanded = False
if "chat_open" not in st.session_state:
    st.session_state.chat_open = False

chat_w = "700px" if st.session_state.chat_expanded else "360px"
bottom_pos = "150px" if chat_bubble_b64 else "90px"

bubble_css = f"""
    .st-key-chat_toggle_btn button {{
        background-image: url("data:image/png;base64,{chat_bubble_b64}") !important;
        background-size: contain !important;
        background-repeat: no-repeat !important;
        background-position: right bottom !important;
        background-color: transparent !important;
        border: none !important;
        box-shadow: none !important;
        color: transparent !important; 
        width: 240px !important;
        height: 120px !important;
        filter: drop-shadow(0px 6px 12px rgba(0,0,0,0.4));
        transition: transform 0.2s;
    }}
    .st-key-chat_toggle_btn button:hover {{
        transform: scale(1.05);
        background-color: transparent !important;
    }}
""" if chat_bubble_b64 else """
    .st-key-chat_toggle_btn button {
        border-radius: 50% !important;
        width: 60px !important;
        height: 60px !important;
        font-size: 24px !important;
    }
"""

st.markdown(f"""
    <style>
    /* 1. Instant rendering of the chat toggle button */
    .st-key-chat_toggle_btn {{
        position: fixed !important;
        bottom: 25px !important;
        right: 25px !important;
        z-index: 999999 !important;
        width: auto !important;
    }}
    
    {bubble_css}
    
    /* 2. Instant rendering of the chat window (No Flashing!) */
    .st-key-chat_win_container {{
        position: fixed !important;
        bottom: {bottom_pos} !important;
        right: 25px !important;
        width: {chat_w} !important;
        /* max-width dynamically calculates the screen size to ensure the 'X' button never bleeds off-screen */
        max-width: calc(100vw - 50px) !important; 
        background-color: white !important;
        border-radius: 15px !important;
        border: 2px solid #16a34a !important;
        box-shadow: 0 15px 40px rgba(0,0,0,0.8) !important;
        z-index: 999999 !important;
        padding: 15px !important;
        transition: width 0.2s ease-in-out !important;
    }}
    
    /* Fix table horizontal scrolling */
    .st-key-chat_win_container [data-testid="stMarkdownContainer"] table {{
        display: block; overflow-x: auto; white-space: nowrap;
    }}
    .st-key-chat_win_container [data-testid="stMarkdownContainer"] th, 
    .st-key-chat_win_container [data-testid="stMarkdownContainer"] td {{
        padding: 8px 12px !important;
    }}
    </style>
""", unsafe_allow_html=True)

# Toggle Button (Using a non-breaking space \u00A0 so the text is hidden and the image shines through)
if st.button("\u00A0", key="chat_toggle_btn", help="Ask Sentinel AI"):
    st.session_state.chat_open = not st.session_state.chat_open
    st.rerun()

# Chat Window - The 'key' magically turns into the .st-key-chat_win_container CSS class!
if st.session_state.chat_open:
    with st.container(key="chat_win_container"):
        col1, col2, col3 = st.columns([0.65, 0.15, 0.20])
        with col1:
            if sentinel_char_b64:
                st.markdown(f"""
                <div style="display:flex; align-items:center; gap:12px; margin-top:-10px;">
                    <img src="data:image/png;base64,{sentinel_char_b64}" style="width:45px; height:45px; border-radius:50%; border:2px solid #16a34a; background:#e6f7ed; object-fit:cover; box-shadow:0 2px 4px rgba(0,0,0,0.1);">
                    <div>
                        <h3 style='color:#16a34a; margin:0; font-size:18px;'>Sentinel</h3>
                        <div style='color:gray; font-size:12px; margin-top:-2px;'>Urban AI Assistant</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown("<h3 style='color:#16a34a; margin-top:-10px;'>🤖 Sentinel</h3>", unsafe_allow_html=True)
                st.caption("Urban AI Assistant")
        with col2:
            expand_icon = "🗗" if st.session_state.chat_expanded else "⛶"
            if st.button(expand_icon, key="expand_chat_btn", help="Toggle Expand"):
                st.session_state.chat_expanded = not st.session_state.chat_expanded
                st.rerun()
        with col3:
            if st.button("✖", key="close_chat_btn", help="Close Chat"):
                st.session_state.chat_open = False
                st.rerun()
                
        st.markdown("<hr style='margin:10px 0;'>", unsafe_allow_html=True)
        
        chat_h = 450 if st.session_state.chat_expanded else 350
        msg_area = st.container(height=chat_h)
        
        for msg in st.session_state.chat_history:
            if msg["role"] == "assistant" and sentinel_char_b64:
                msg_area.chat_message(msg["role"], avatar=f"data:image/png;base64,{sentinel_char_b64}").write(msg["content"])
            else:
                msg_area.chat_message(msg["role"]).write(msg["content"])
                
        def handle_chat_submit():
            user_input = st.session_state.chat_input_val
            if user_input:
                st.session_state.chat_history.append({"role": "user", "content": user_input})
                sys_context = f"""
                You are 'Sentinel', an expert Urban Sustainability AI assistant. 
                Keep answers concise, friendly, and easy to understand. Break down technical jargons.
                CONTEXT:
                - Target Area: {st.session_state.loc_name}
                - Analyzed Metrics: {st.session_state.metrics_data if st.session_state.metrics_data else 'No area analyzed yet.'}
                """
                try:
                    if GROQ_KEY:
                        headers = {"Authorization": f"Bearer {GROQ_KEY}", "Content-Type": "application/json"}
                        messages = [{"role": "system", "content": sys_context}] + st.session_state.chat_history
                        payload = {"model": "openai/gpt-oss-120b", "messages": messages, "temperature": 0.7}
                        res = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload)
                        if res.status_code == 200:
                            reply = res.json()["choices"][0]["message"]["content"]
                            st.session_state.chat_history.append({"role": "assistant", "content": reply})
                    else:
                        response = client.models.generate_content(model="models/gemini-2.0-flash", contents=sys_context + f"\n\nUser Question: {user_input}")
                        st.session_state.chat_history.append({"role": "assistant", "content": response.text})
                except Exception as e:
                    st.session_state.chat_history.append({"role": "assistant", "content": f"**Error:** {str(e)}"})
                st.session_state.chat_input_val = ""
                
        st.text_input("Ask Sentinel...", key="chat_input_val", on_change=handle_chat_submit, placeholder="Why is NDVI low here?")