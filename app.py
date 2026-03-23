import streamlit as st
import pandas as pd
import requests
import pydeck as pdk
import io

# --- 1. APP CONFIGURATION ---
st.set_page_config(page_title="Toronto Traffic Scope", layout="wide", page_icon="🍁")

st.markdown("""
    <style>
    .main-title { font-size: 32px; font-weight: bold; color: #E31837; }
    .subtitle { font-size: 16px; color: #555; margin-bottom: 20px;}
    </style>
    """, unsafe_allow_html=True)

st.markdown('<p class="main-title">🍁 Toronto Traffic Data Dashboard</p>', unsafe_allow_html=True)
st.markdown('<p class="subtitle">Visualizing official City of Toronto traffic volumes and road restrictions.</p>', unsafe_allow_html=True)

# --- 2. ROBUST DATA LOADING ---
@st.cache_data(ttl=3600)
def get_traffic_data():
    """Fetches traffic volume data with a guaranteed demo fallback."""
    try:
        url = "https://ckan0.cf.opendata.inter.prod-toronto.ca"
        df = pd.read_csv(url)
        return clean_data(df)
    except:
        # Emergency Demo Data
        data = """counting_date,main_street,side_1_street,8hr_vehicle_volume,lat,lng
        2024-05-20,YONGE ST,DUNDAS ST,28500,43.6561,-79.3802
        2024-06-01,LAKE SHORE BLVD,BATHURST ST,34000,43.6356,-79.3995
        2024-06-15,BLOOR ST,SPADINA AVE,22000,43.6662,-79.4032
        """
        return clean_data(pd.read_csv(io.StringIO(data)))

def clean_data(df):
    """Fixes coordinates and standardizes columns."""
    df = df.rename(columns={'latitude': 'lat', 'Latitude': 'lat', 'longitude': 'lng', 'Longitude': 'lng'})
    if '8hr_vehicle_volume' not in df.columns:
        vol_cols = [c for c in df.columns if 'volume' in c.lower()]
        df['8hr_vehicle_volume'] = df[vol_cols[0]] if vol_cols else 1000
    df['counting_date'] = pd.to_datetime(df['counting_date'], errors='coerce')
    return df.dropna(subset=['lat', 'lng'])

# --- 3. SIDEBAR & FILTERS ---
view = st.sidebar.radio("Navigation:", ["Traffic Volumes", "Road Restrictions"])
df = get_traffic_data()

if view == "Traffic Volumes":
    st.sidebar.subheader("Map Filters")
    query = st.sidebar.text_input("Search Street:", "").upper()
    min_vol = st.sidebar.slider("Min Volume:", 0, 25000, 5000)
    
    # Filter Logic
    mask = (df['8hr_vehicle_volume'] >= min_vol)
    if query:
        mask &= (df['main_street'].str.contains(query, na=False) | df['side_1_street'].str.contains(query, na=False))
    filtered_df = df[mask]

    # --- 4. MAP RENDERING ---
    st.subheader(f"🚦 Intersection Analysis ({len(filtered_df)} results)")
    
    try:
        st.pydeck_chart(pdk.Deck(
            map_style='mapbox://styles/mapbox/light-v9', # No token required for basic styles
            initial_view_state=pdk.ViewState(latitude=43.6532, longitude=-79.3832, zoom=12, pitch=45),
            layers=[
                pdk.Layer(
                    'ColumnLayer',
                    data=filtered_df,
                    get_position='[lng, lat]',
                    get_elevation='8hr_vehicle_volume',
                    elevation_scale=0.1,
                    radius=80,
                    get_fill_color=[227, 24, 55, 200], # Toronto Red
                    pickable=True,
                ),
            ],
            tooltip={"text": "{main_street} & {side_1_street}\nVolume: {8hr_vehicle_volume}"}
        ))
    except Exception as e:
        st.error(f"Map Error: {e}. Try refreshing the page.")

    st.dataframe(filtered_df.sort_values('8hr_vehicle_volume', ascending=False), use_container_width=True)

elif view == "Road Restrictions":
    st.subheader("🚧 Live Toronto Road Notices")
    try:
        r = requests.get("https://app.toronto.ca", timeout=10)
        notices = pd.DataFrame(r.json().get('notices', []))
        if not notices.empty:
            st.dataframe(notices[['road', 'description', 'severity']], use_container_width=True)
        else:
            st.success("No active road restrictions.")
    except:
        st.warning("Live data currently unavailable.")
    
