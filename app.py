import streamlit as st
import pandas as pd
import requests
import pydeck as pdk
import io

# --- APP CONFIGURATION ---
st.set_page_config(page_title="Toronto Traffic Scope", layout="wide", page_icon="🍁")
st.title("🍁 Toronto Traffic Data Dashboard")
st.markdown("Digitally visualize official traffic reports and road restrictions from the City of Toronto.")

# --- ROBUST DATA FETCHING ---
@st.cache_data
def get_traffic_volumes():
    """
    Triple-Safe Strategy:
    1. Try Direct API (Best for freshness)
    2. Try Hardcoded Direct Link (Bypasses search blocks)
    3. Fallback to Sample Data (Ensures app never crashes)
    """
    status = st.empty()
    
    # --- STRATEGY 1: DIRECT API (Often blocked on Cloud) ---
    status.info("Trying to connect to City Database...")
    try:
        api_url = "https://ckan0.cf.opendata.inter.prod-toronto.ca"
        params = {"id": "traffic-volumes-at-intersections-for-all-modes"}
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        
        r = requests.get(api_url, params=params, headers=headers, timeout=5)
        if r.status_code == 200:
            resources = r.json()["result"]["resources"]
            for res in resources:
                if "most_recent_summary" in res["name"].lower() and res["format"].lower() == "csv":
                    df = pd.read_csv(res["url"])
                    status.success("Connected to Live City API!")
                    return clean_data(df)
    except:
        pass

    # --- STRATEGY 2: HARDCODED MIRROR (The Fix) ---
    # This links directly to the file, skipping the "search" step that gets blocked.
    status.warning("API blocked. Trying direct download link...")
    try:
        # This is the known stable link for the summary dataset
        direct_url = "https://ckan0.cf.opendata.inter.prod-toronto.ca"
        df = pd.read_csv(direct_url, on_bad_lines='skip')
        status.success("Loaded via Direct Link.")
        return clean_data(df)
    except:
        pass

    # --- STRATEGY 3: GENERATE SAMPLE DATA (Failsafe) ---
    status.error("City servers are completely blocking connections. Loading Demo Data.")
    data = """counting_date,main_street,side_1_street,8hr_vehicle_volume,lat,lng
    2024-05-20,YONGE ST,DUNDAS ST,25000,43.6561,-79.3802
    2024-05-21,BLOOR ST,SPADINA AVE,21000,43.6662,-79.4032
    2024-06-01,LAKE SHORE BLVD,BATHURST ST,32000,43.6356,-79.3995
    2024-06-15,QUEEN ST,UNIVERSITY AVE,18500,43.6509,-79.3865
    2024-07-10,EGLINTON AVE,DON MILLS RD,29000,43.7233,-79.3371
    2024-07-12,SHEPPARD AVE,YONGE ST,27500,43.7615,-79.4109
    2024-08-05,KING ST,JARVIS ST,15000,43.6504,-79.3718
    2023-11-20,FRONT ST,BAY ST,19000,43.6467,-79.3792
    """
    df = pd.read_csv(io.StringIO(data))
    return clean_data(df)

def clean_data(df):
    """Standardizes column names and formats dates."""
    # Fix coordinates
    col_map = {'latitude': 'lat', 'Latitude': 'lat', 'longitude': 'lng', 'Longitude': 'lng'}
    df = df.rename(columns=col_map)
    
    # Find volume column (it changes names sometimes)
    if '8hr_vehicle_volume' not in df.columns:
        # Find first column with 'volume' in it
        vol_cols = [c for c in df.columns if 'volume' in c.lower()]
        if vol_cols:
            df['8hr_vehicle_volume'] = df[vol_cols[0]]
        else:
            df['8hr_vehicle_volume'] = 1000 # Fallback

    # Fix dates
    if 'counting_date' in df.columns:
        df['counting_date'] = pd.to_datetime(df['counting_date'], errors='coerce')
        df = df.sort_values('counting_date', ascending=False)
    
    return df.dropna(subset=['lat', 'lng'])

# --- MAIN INTERFACE ---
view_option = st.sidebar.radio("Select Report:", ["Intersection Volumes", "Live Road Restrictions"])

if view_option == "Intersection Volumes":
    st.subheader("🚦 Intersection Traffic Volumes")
    
    df_vol = get_traffic_volumes()
    
    if df_vol is not None:
        # Filters
        col1, col2 = st.columns(2)
        with col1:
            # Year Slider
            min_year = int(df_vol['counting_date'].dt.year.min())
            max_year = int(df_vol['counting_date'].dt.year.max())
            sel_year = st.slider("Show data from year:", min_year, max_year, min_year)
        
        with col2:
            # Volume Slider
            max_vol = int(df_vol['8hr_vehicle_volume'].max())
            min_vol = st.slider("Min Volume:", 0, max_vol, 5000)

        # Apply Filter
        mask = (df_vol['counting_date'].dt.year >= sel_year) & (df_vol['8hr_vehicle_volume'] >= min_vol)
        filtered = df_vol[mask]
        
        st.write(f"Showing {len(filtered)} intersections.")

        # Map
        st.pydeck_chart(pdk.Deck(
            map_style='mapbox://styles/mapbox/light-v9',
            initial_view_state=pdk.ViewState(
                latitude=43.70, longitude=-79.42, zoom=11, pitch=50,
            ),
            layers=[
                pdk.Layer(
                    'ColumnLayer',
                    data=filtered,
                    get_position='[lng, lat]',
                    get_elevation='8hr_vehicle_volume',
                    elevation_scale=0.3,
                    radius=150,
                    get_fill_color='[255, 75, 75, 200]',
                    pickable=True,
                    auto_highlight=True,
                ),
            ],
            tooltip={"text": "{main_street} & {side_1_street}\nVol: {8hr_vehicle_volume}\nDate: {counting_date}"}
        ))
        
        st.dataframe(filtered[['counting_date', 'main_street', 'side_1_street', '8hr_vehicle_volume']].head(50), use_container_width=True)

elif view_option == "Live Road Restrictions":
    st.subheader("🚧 Live Road Closures")
    try:
        r = requests.get("https://secure.toronto.ca")
        df = pd.DataFrame(r.json()['notices'])
        st.dataframe(df[['road', 'description', 'start_date', 'end_date']])
    except:
        st.write("No live notices available.")
        
