import os
import json
import requests
import base64
import random
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

# ---------------------------------------------------------
# 1. SETUP & CONFIGURATION
# ---------------------------------------------------------
# Let's set up the main page. 'wide' layout is crucial here because 
# we want our map to feel like a massive, immersive dashboard.
st.set_page_config(page_title="Project Sentinel | Urban GIS", layout="wide", page_icon=None, initial_sidebar_state="expanded")

# Load up our secret keys from the .env file. Never hardcode these!
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(dotenv_path=BASE_DIR / ".env", override=True)

CLIENT_ID = os.getenv("SENTINEL_CLIENT_ID") 
CLIENT_SECRET = os.getenv("SENTINEL_CLIENT_SECRET") 
GEMINI_KEY = os.getenv("GEMINI_API_KEY") 
GROQ_KEY = os.getenv("GROQ_API_KEY") 

# Initialize our Chief Urban Scientist (Gemini 2.0 Flash)
client = genai.Client(api_key=GEMINI_KEY)

# ---------------------------------------------------------
# 2. CORE SESSION STATE (OUR APP'S MEMORY)
# ---------------------------------------------------------
# Streamlit re-runs the entire script every time a button is clicked. 
# We use st.session_state as our "memory bank" so it doesn't forget 
# where we placed our map pin or what the AI analyzed.

# Default starting coordinates (NU Manila!)
if "lat" not in st.session_state: st.session_state.lat = 14.60420
if "lon" not in st.session_state: st.session_state.lon = 120.98930
if "loc_name" not in st.session_state: st.session_state.loc_name = "NU Manila"
if "radius_m" not in st.session_state: st.session_state.radius_m = 500
if "start_date" not in st.session_state: st.session_state.start_date = datetime.now().date() - timedelta(days=90)
if "custom_bbox" not in st.session_state: st.session_state.custom_bbox = None
if "analyzed" not in st.session_state: st.session_state.analyzed = False
if "simulated_data" not in st.session_state: st.session_state.simulated_data = False

# Memory for the AI Assistant so it remembers the conversation context
if "metrics_data" not in st.session_state: st.session_state.metrics_data = None
if "analysis_data" not in st.session_state: st.session_state.analysis_data = None
if "chat_open" not in st.session_state: st.session_state.chat_open = False
if "chat_history" not in st.session_state:
    st.session_state.chat_history = [
        {"role": "assistant", "content": "Hello! I am Sentinel. Ask me to explain the satellite data, decode jargon, or evaluate project feasibility!"}
    ]

# ---------------------------------------------------------
# 3. IMAGE LOADER (ASSETS)
# ---------------------------------------------------------
# We convert images to Base64 so we can inject them directly into our custom HTML/CSS 
# without worrying about file path errors when deploying to the cloud.
@st.cache_data
def get_image_b64(filenames):
    for fn in filenames:
        if os.path.exists(fn):
            with open(fn, "rb") as f:
                return base64.b64encode(f.read()).decode()
    return ""

logo_base64 = get_image_b64(["Untitled design-3.png", "Untitled design-3.jpg"])
title_logo_base64 = get_image_b64(["Project Sentinel Font.png", "Project Sentinel Font.jpg"])
chat_bubble_b64 = get_image_b64(["ProjectSentinelChat-3.png", "ProjectSentinelChat-3.jpg", "Project Sentinel Chat-3.png", "Project Sentinel Chat-3.jpg"])
sentinel_char_b64 = get_image_b64(["Sentinel-3.png", "Sentinel-3.jpg", "Sentinel 3.png", "Sentinel 3.jpg"])

# ---------------------------------------------------------
# 4. GLOBAL CSS HACKS (MAKING IT LOOK LIKE A PRO SAAS)
# ---------------------------------------------------------
# Streamlit is great, but its default padding ruins the fullscreen map vibe. 
# Here, we obliterate the margins, hide the footer, and force our dark green branding globally.
st.markdown("""
    <style>
    .stApp, [data-testid="stMain"], .main { background-color: #e6f7ed !important; }
    
    /* === TRUE FULLSCREEN MAP CONTROLS - OBLITERATE ALL PADDING === */
    .block-container, .main .block-container, [data-testid="stAppViewBlockContainer"] { 
        padding-top: 0rem !important;
        padding-bottom: 0rem !important;
        padding-left: 0rem !important;
        padding-right: 0rem !important;
        margin-top: 0rem !important;
        margin-bottom: 0rem !important;
        max-width: 100% !important; 
    }
    
    /* Streamlit injects an invisible 6rem gap for the header. This forces it to 0. */
    [data-testid="stAppViewContainer"] > .main > div:first-child {
        padding-top: 0rem !important;
        padding-bottom: 0rem !important;
        gap: 0rem !important;
    }
    
    footer { display: none !important; } 
    header[data-testid="stHeader"] { background: transparent !important; height: 0px !important; }
    header[data-testid="stHeader"] * { color: transparent !important; } 
    
    [data-testid="stSidebar"] { background-color: #e6f7ed; border-right: none !important; box-shadow: none !important; width: 400px !important; }
    [data-testid="stSidebarUserContent"] { padding-top: 0rem !important; }
    .sidebar-header { margin-top: -10px; margin-bottom: 10px; }
    
    /* === APPLY DARK GREEN FONT GLOBALLY === */
    .stMarkdown p, .stMarkdown h1, .stMarkdown h2, .stMarkdown h3, .stMarkdown h4, .stMarkdown h5, .stMarkdown h6, 
    label, .st-emotion-cache-1wivap2, [data-testid="stMetricLabel"] > div, 
    [data-testid="stMetricValue"] > div, .stCaption {
        color: #166534 !important;
    }
    
    label p, .stTextInput label p, .stNumberInput label p { font-weight: 900 !important; }
    label { font-weight: bold !important; }
    
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
    
    iframe { display: block; border: none !important; position: relative; z-index: 0 !important; margin: 0 !important; padding: 0 !important;}
    </style>
    """, unsafe_allow_html=True)

# ---------------------------------------------------------
# 5. UTILS & ENGINES (THE GEOSPATIAL BRAIN)
# ---------------------------------------------------------
# First, we need a fresh token from Copernicus to access the satellites.
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

# Here is where we actually talk to space. We use st.cache_data so we don't 
# spam the API if the user runs the exact same location twice.
@st.cache_data(ttl=3600, show_spinner=False)
def fetch_satellite_metrics(bbox_coords, start_date):
    st.session_state.simulated_data = False
    token = get_sentinel_token()
    
    # Failsafe: If the API is down or we hit a cloud-cover wall, we generate 
    # simulated Philippine baseline data so the MVP demo doesn't crash on stage.
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
    
    # Calculate the exact timeframe the user requested.
    end_date = datetime.utcnow()
    from_date = start_date.strftime("%Y-%m-%dT00:00:00Z")
    to_date = end_date.strftime("%Y-%m-%dT23:59:59Z")
    
    # We compress ALL the images taken during this timeframe into one clean statistical average
    days_diff = max(1, (end_date.date() - start_date).days)
    interval_str = f"P{days_diff}D"
    
    # This is the V3 Evalscript. Instead of downloading gigabytes of imagery, 
    # we tell the Copernicus server to just send us the 6 spectral bands we need.
    evalscript = """
    //VERSION=3
    function setup() {
        return { input: [{bands: ["B02", "B03", "B04", "B08", "B8A", "B11", "dataMask"]}], output: [{ id: "default", bands: 6, sampleType: "FLOAT32" }, { id: "dataMask", bands: 1 }] };
    }
    function evaluatePixel(sample) {
        return { default: [sample.B02, sample.B03, sample.B04, sample.B08, sample.B8A, sample.B11], dataMask: [sample.dataMask] };
    }
    """
    
    # Try the high-quality L2A atmospheric corrected data first. If it fails, fallback to L1C.
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
                    
                    # Calculate the actual scientific indices using the band math
                    return {
                        "NDVI": round((b08 - b04) / (b08 + b04), 4) if (b08 + b04) != 0 else 0, 
                        "NDWI": round((b03 - b08) / (b03 + b08), 4) if (b03 + b08) != 0 else 0,
                        "NDBI": round((b11 - b08) / (b11 + b08), 4) if (b11 + b08) != 0 else 0,
                        "NDMI": round((b8a - b11) / (b8a + b11), 4) if (b8a + b11) != 0 else 0,
                        "quality": col.upper()
                    }
        except: continue
        
    return generate_fallback() 

# ---------------------------------------------------------
# 6. AI SYNTHESIS (THE ANALYTICAL BRAIN)
# ---------------------------------------------------------
# Now we pass the raw math to Gemini. We strictly instruct it to act as an Urban Scientist
# and force it to return a JSON so we can easily parse it into our UI later.
@st.cache_data(ttl=3600, show_spinner=False)
def get_ai_analysis(metrics, location, base_lat, base_lon, area_context):
    models_to_try = ["models/gemini-2.0-flash", "models/gemini-3-flash-preview"]
    prompt = f"""
You are a Chief Urban Sustainability Scientist specializing in Philippine urban environments.
LOCATION: {location} ({base_lat}, {base_lon}) | Context: {area_context}
SATELLITE METRICS: NDVI: {metrics['NDVI']} | NDWI: {metrics['NDWI']} | NDBI: {metrics['NDBI']} | NDMI: {metrics['NDMI']}

INTERPRETATION RULES (STRICT):
NDVI: <0.2=very low, 0.2–0.5=moderate, >0.5=high
NDBI: >0.3=highly urbanized, 0.1–0.3=mixed, <0.1=non-urban
NDWI: >0.2=high water/flood risk, 0–0.2=moderate, <0=dry
NDMI: >0.3=high moisture, 0–0.3=moderate, <0=dry

EVALUATE THESE PROJECTS: 1. Urban Green Park, 2. Commercial Infrastructure, 3. Residential Development, 4. Flood Control System, 5. Agricultural Use
DECISION REQUIREMENTS: Base strictly on metrics. Consider PH conditions. Be conservative.
OUTPUT STRICT JSON ONLY:
{{
  "feasibility_scores": [{{ "project": "string", "status": "RECOMMENDED | WITH MITIGATION | NOT RECOMMENDED", "reason": "string" }}],
  "full_report_markdown": "Professional markdown report"
}}
"""
    for model_name in models_to_try:
        try:
            response = client.models.generate_content(model=model_name, contents=prompt, config=types.GenerateContentConfig(response_mime_type="application/json"))
            return json.loads(response.text)
        except: continue
    return None

# ---------------------------------------------------------
# 7. MAIN EXECUTION PIPELINE
# ---------------------------------------------------------
# This block runs when the user clicks "Run Assessment". It determines if we are 
# scanning a custom drawn polygon or just generating a radius around a dropped pin.
bbox_to_use = None
area_context = ""

if st.session_state.analyzed:
    if st.session_state.custom_bbox:
        bbox_to_use = st.session_state.custom_bbox
        area_context = "Custom User-Drawn Rectangle"
    else:
        # Convert meters into map coordinate offsets
        offset = st.session_state.radius_m / 111320.0
        bbox_to_use = [
            st.session_state.lon - offset, st.session_state.lat - offset, 
            st.session_state.lon + offset, st.session_state.lat + offset
        ]
        sq_km = ((st.session_state.radius_m * 2) / 1000) ** 2
        area_context = f"Calculated {st.session_state.radius_m}m radius buffer (~{sq_km:.2f} sq km)"

    # Fire off the APIs and store the results in our memory bank
    with st.spinner("🛰️ Executing Geospatial Pipeline..."):
        metrics = fetch_satellite_metrics(bbox_to_use, st.session_state.start_date)
        if metrics:
            st.session_state.metrics_data = metrics
            analysis = get_ai_analysis(metrics, st.session_state.loc_name, st.session_state.lat, st.session_state.lon, area_context)
            if analysis:
                st.session_state.analysis_data = analysis
            else:
                st.error("Gemini AI Analysis Failed. Check your API Key.")
                st.session_state.analyzed = False
        else:
            st.session_state.analyzed = False

# ---------------------------------------------------------
# 8. UI: SIDEBAR (THE CONTROL PANEL)
# ---------------------------------------------------------
# This builds the left-hand menu where the user interacts with the app.
with st.sidebar:
    # Inject our awesome custom branding logos at the top
    if logo_base64 and title_logo_base64:
        st.markdown(
            f'<div style="position: relative; height: 10px; margin-top: -20px;">'
            f'<img src="data:image/png;base64,{logo_base64}" style="position: absolute; top: -80px; left: 183px; width: 0px; z-index: 10; pointer-events: none;">'
            f'<img src="data:image/png;base64,{title_logo_base64}" style="position: absolute; top: -200px; left: -40px; width: 500px; z-index: 10; pointer-events: none;">'
            f'</div>', unsafe_allow_html=True
        )
    
    tab_search, tab_assess = st.tabs([" SEARCH & CONTROLS", " ASSESSMENT RESULTS"])
    
    # TAB 1: Inputs
    with tab_search:
        st.markdown("### Location Settings")
        loc_name_input = st.text_input(" Location Name", value=st.session_state.loc_name)
        lat_input = st.number_input(" Latitude", value=st.session_state.lat, format="%.6f", step=0.0001)
        lon_input = st.number_input(" Longitude", value=st.session_state.lon, format="%.6f", step=0.0001)
        
        st.markdown("**Area Boundaries:**")
        radius_input = st.number_input(" Area Radius (meters)", value=st.session_state.radius_m, min_value=100, max_value=10000, step=100)

        st.markdown("**Time Frame:**")
        start_date_input = st.date_input(" Start Date", value=st.session_state.start_date, max_value=datetime.now().date())
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        # When this is clicked, we update the state and force a re-run to trigger the pipeline block above
        if st.button("Run Assessment", use_container_width=True, type="primary"):
            st.session_state.lat = lat_input
            st.session_state.lon = lon_input
            st.session_state.loc_name = loc_name_input
            st.session_state.radius_m = radius_input
            st.session_state.start_date = start_date_input
            st.session_state.analyzed = True
            st.rerun()

    # TAB 2: Outputs
    with tab_assess:
        if not st.session_state.analyzed:
            st.info("👈 Set your location and click 'Run Analysis' to generate data.")
        elif st.session_state.metrics_data and st.session_state.analysis_data:
            m_data = st.session_state.metrics_data
            a_data = st.session_state.analysis_data
            
            if st.session_state.simulated_data:
                st.warning("⚠️ **Using Simulated Data:** Copernicus API unavailable or no clear image found.")
            
            # Display the raw satellite math as progress bars for easy reading
            st.markdown("### Satellite Indices")
            c1, c2 = st.columns(2)
            c1.metric("NDVI (Flora)", m_data['NDVI'])
            c1.progress(min(max((m_data['NDVI'] + 1) / 2, 0), 1))
            c2.metric("NDBI (Urban)", m_data['NDBI'])
            c2.progress(min(max((m_data['NDBI'] + 1) / 2, 0), 1))

            c3, c4 = st.columns(2)
            c3.metric("NDWI (Water)", m_data['NDWI'])
            c3.progress(min(max((m_data['NDWI'] + 1) / 2, 0), 1))
            c4.metric("NDMI (Moist)", m_data['NDMI'])
            c4.progress(min(max((m_data['NDMI'] + 1) / 2, 0), 1))
            
            st.divider()
            
            # Display the AI's grading logic (Parsed from the JSON)
            st.markdown("###  Feasibility Status")
            if "feasibility_scores" in a_data:
                for item in a_data["feasibility_scores"]:
                    color = "red" if item['status'] == "RECOMMENDED" else "orange" if "MITIGATION" in item['status'] else "orange"
                    st.markdown(f"**{item['project']}**")
                    st.markdown(f"<span style='color:{color}; font-weight:bold;'>{item['status']}</span>", unsafe_allow_html=True)
                    st.caption(item['reason'])
                    st.markdown("<hr style='margin:10px 0px; border-color:#dcfce7;'>", unsafe_allow_html=True)

            with st.expander(" Read Executive Report"):
                if "full_report_markdown" in a_data:
                    st.markdown(a_data["full_report_markdown"])

# ---------------------------------------------------------
# 9. UI: MAIN SCREEN (FOLIUM MAP)
# ---------------------------------------------------------
# Set up the Folium map centered on our current coordinates
m = folium.Map(location=[st.session_state.lat, st.session_state.lon], zoom_start=16, tiles='https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}', attr='Google')
m.get_root().html.add_child(Element("<style>.leaflet-top.leaflet-right { margin-top: 20px !important; padding-right: 10px !important; }</style>"))

# Add interactive plugins so the user can search addresses or draw polygons
Geocoder(position='topright', add_marker=True).add_to(m)
Fullscreen(position='topright').add_to(m)
Draw(export=False, position='topright', draw_options={'polyline': False, 'polygon': False, 'rectangle': True, 'circle': False, 'marker': True, 'circlemarker': False}, edit_options={'edit': True, 'remove': True}).add_to(m)

# If an analysis is active, draw a cool green box showing exactly what area the satellite scanned
if st.session_state.analyzed and bbox_to_use:
    min_lon, min_lat, max_lon, max_lat = bbox_to_use
    visual_bbox = [[min_lat, min_lon], [max_lat, min_lon], [max_lat, max_lon], [min_lat, max_lon]]
    folium.Polygon(locations=visual_bbox, color="#16a34a", weight=3, fill=True, fill_opacity=0.2).add_to(m)
    pin_lat = (min_lat + max_lat) / 2 if st.session_state.custom_bbox else st.session_state.lat
    pin_lon = (min_lon + max_lon) / 2 if st.session_state.custom_bbox else st.session_state.lon
    folium.Marker([pin_lat, pin_lon], popup=st.session_state.loc_name, icon=folium.Icon(color='green')).add_to(m)
else:
    folium.Marker([st.session_state.lat, st.session_state.lon], popup=st.session_state.loc_name, icon=folium.Icon(color='green')).add_to(m)

# Render the map into Streamlit! Height is massive (1200) to force it off the bottom of the screen.
map_data = st_folium(m, use_container_width=True, height=1200, key="main_map", returned_objects=["all_drawings"])

# Extract drawing data: If the user drops a pin or draws a box, update the backend so we scan that exact spot.
if map_data and "all_drawings" in map_data:
    drawings = map_data["all_drawings"]
    if drawings and len(drawings) > 0:
        geom = drawings[-1]["geometry"]
        if geom["type"] == "Polygon":
            coords = geom["coordinates"][0]
            lons, lats = [c[0] for c in coords], [c[1] for c in coords]
            st.session_state.custom_bbox = [min(lons), min(lats), max(lons), max(lats)]
        elif geom["type"] == "Point":
            new_lon, new_lat = geom["coordinates"]
            if round(st.session_state.lat, 4) != round(new_lat, 4) or round(st.session_state.lon, 4) != round(new_lon, 4):
                st.session_state.lat = new_lat
                st.session_state.lon = new_lon
                st.session_state.loc_name = f"Custom Pinned Location ({new_lat:.4f}, {new_lon:.4f})"
                st.session_state.custom_bbox = None 
                st.session_state.analyzed = False    
                st.rerun()
    elif drawings is not None and len(drawings) == 0:
        st.session_state.custom_bbox = None

# ---------------------------------------------------------
# 10. UI: FLOATING CHAT WIDGET (THE CONVERSATIONAL BRAIN)
# ---------------------------------------------------------
# We create a container and drop a span marker so our Javascript (below) can find it and move it around the screen.
chat_btn_container = st.container()
with chat_btn_container:
    st.markdown('<span id="chat-btn-wrapper"></span>', unsafe_allow_html=True)
    if st.button("💬", key="chat_toggle_btn"):
        st.session_state.chat_open = not st.session_state.chat_open
        st.rerun()

# If the chat is toggled open, build the actual window UI
if st.session_state.chat_open:
    chat_win_container = st.container()
    with chat_win_container:
        st.markdown('<span id="chat-win-wrapper"></span>', unsafe_allow_html=True)
        
        col1, col2 = st.columns([0.85, 0.15])
        with col1:
            # Custom Header with your Sentinel Character Avatar
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
            if st.button("X", key="close_chat_btn"):
                st.session_state.chat_open = False
                st.rerun()
        
        st.markdown("<hr style='margin:10px 0;'>", unsafe_allow_html=True)
        
        # Render the chat history loop
        msg_area = st.container(height=350)
        for msg in st.session_state.chat_history:
            if msg["role"] == "assistant" and sentinel_char_b64:
                msg_area.chat_message(msg["role"], avatar=f"data:image/png;base64,{sentinel_char_b64}").write(msg["content"])
            else:
                msg_area.chat_message(msg["role"]).write(msg["content"])
        
        # When the user submits a question, we silently inject the current satellite metrics
        # into the system prompt. This gives the AI perfect context of the map!
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
                - Feasibility Report: {st.session_state.analysis_data if st.session_state.analysis_data else 'No report available yet.'}
                """
                
                try:
                    # We use Groq (Llama 3.1) here because LPU inference is incredibly fast, 
                    # making the chat feel like a real conversation.
                    if GROQ_KEY:
                        headers = {"Authorization": f"Bearer {GROQ_KEY}", "Content-Type": "application/json"}
                        messages = [{"role": "system", "content": sys_context}] + st.session_state.chat_history
                        payload = {"model": "llama-3.1-8b-instant", "messages": messages, "temperature": 0.7}
                        res = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload)
                        if res.status_code == 200:
                            reply = res.json()["choices"][0]["message"]["content"]
                            st.session_state.chat_history.append({"role": "assistant", "content": reply})
                        else:
                            st.session_state.chat_history.append({"role": "assistant", "content": f"**Groq API Error:** {res.text}"})
                    else:
                        # Fallback to Gemini if Groq isn't configured
                        response = client.models.generate_content(model="models/gemini-2.0-flash", contents=sys_context + f"\n\nUser Question: {user_input}")
                        st.session_state.chat_history.append({"role": "assistant", "content": response.text})
                except Exception as e:
                    st.session_state.chat_history.append({"role": "assistant", "content": f"**Connection Error:** {str(e)}"})
                
                st.session_state.chat_input_val = ""

        st.text_input("Ask Sentinel...", key="chat_input_val", on_change=handle_chat_submit, placeholder="Why is NDVI low here?")

# ---------------------------------------------------------
# 11. JAVASCRIPT INJECTOR (THE UI HACK)
# ---------------------------------------------------------
# Streamlit does not natively allow floating elements to hover OVER other elements (like the map).
# To fix this, we use Python to write a custom Javascript script that reaches out of the iframe, 
# grabs our chat widget, and violently applies CSS to force it into a fixed Z-index position in the bottom left corner.
js_code = f"""
    <script>
        const doc = window.parent.document;
        
        function forceChatWidgetStyles() {{
            // --- STYLE THE CHAT BUTTON BUBBLE ---
            const btnMarker = doc.getElementById('chat-btn-wrapper');
            if (btnMarker) {{
                const btnContainer = btnMarker.closest('[data-testid="stVerticalBlock"]');
                if (btnContainer) {{
                    btnContainer.style.setProperty('position', 'fixed', 'important');
                    btnContainer.style.setProperty('bottom', '25px', 'important');
                    btnContainer.style.setProperty('left', '25px', 'important');
                    btnContainer.style.setProperty('z-index', '2147483647', 'important');
                    btnContainer.style.setProperty('background-color', 'transparent', 'important');
                    btnContainer.style.setProperty('background', 'transparent', 'important');
                    
                    const btn = btnContainer.querySelector('button');
                    if (btn) {{
                        const bubbleB64 = "{chat_bubble_b64}";
                        
                        if (bubbleB64.length > 10) {{
                            if (!btn.innerHTML.includes('<img')) {{
                                btn.innerHTML = `<img src="data:image/png;base64,${{bubbleB64}}" style="width: 100%; height: auto; object-fit: contain; filter: drop-shadow(0px 6px 12px rgba(0,0,0,0.4));">`;
                            }}
                            
                            // Strip native button styling so only our custom image shows
                            btnContainer.style.setProperty('width', '240px', 'important');
                            btn.style.setProperty('width', '240px', 'important');
                            btn.style.setProperty('height', 'auto', 'important');
                            btn.style.setProperty('background-color', 'transparent', 'important');
                            btn.style.setProperty('background', 'transparent', 'important');
                            btn.style.setProperty('border', 'none', 'important');
                            btn.style.setProperty('box-shadow', 'none', 'important');
                            btn.style.setProperty('padding', '0', 'important');
                            
                            // Add a subtle hover bump effect
                            btn.style.setProperty('transition', 'transform 0.2s', 'important');
                            btn.onmouseover = function() {{ this.style.transform = 'scale(1.05)'; }}
                            btn.onmouseout = function() {{ this.style.transform = 'scale(1)'; }}
                        }}
                    }}
                }}
            }}

            // --- STYLE THE OPEN CHAT WINDOW ---
            const winMarker = doc.getElementById('chat-win-wrapper');
            if (winMarker) {{
                const winContainer = winMarker.closest('[data-testid="stVerticalBlock"]');
                if (winContainer) {{
                    winContainer.style.setProperty('position', 'fixed', 'important');
                    const bottomPos = "{chat_bubble_b64}".length > 10 ? '110px' : '115px';
                    winContainer.style.setProperty('bottom', bottomPos, 'important');
                    winContainer.style.setProperty('left', '25px', 'important');
                    winContainer.style.setProperty('width', '360px', 'important');
                    winContainer.style.setProperty('background-color', 'white', 'important');
                    winContainer.style.setProperty('border-radius', '15px', 'important');
                    winContainer.style.setProperty('border', '2px solid #16a34a', 'important');
                    winContainer.style.setProperty('box-shadow', '0 15px 40px rgba(0,0,0,0.8)', 'important');
                    winContainer.style.setProperty('z-index', '2147483647', 'important');
                    winContainer.style.setProperty('padding', '15px', 'important');
                }}
            }}
        }}
        
        // Execute Injector repeatedly to ensure it catches the elements after Streamlit re-renders
        forceChatWidgetStyles();
        setTimeout(forceChatWidgetStyles, 50);
        setTimeout(forceChatWidgetStyles, 250);
    </script>
"""
components.html(js_code, height=0)