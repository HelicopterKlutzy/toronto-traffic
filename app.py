import streamlit as st
import pandas as pd
import requests
import pydeck as pdk
import io

# --- 1. MINIMAL CONFIG ---
st.set_page_config(page_title="Toronto Traffic Scope", layout="wide")

# CSS for the Toronto Red theme
st.markdown("<style>.main-title { color: #E31837; font-weight: bold; font-size: 32px; }</style>", unsafe_allow_html=True)
st.markdown('<p class="main-title">🍁 Toronto Traffic Dashboard</p>', unsafe_allow_html=True)

# --- 2. FAIL-SAFE DATA LOADING ---
@st.cache_data(ttl=3600)
def get_data():
    """Fetches data with immediate fallback to avoid API timeouts."""
    try:
        url = "https://ckan0.cf.opendata.inter.prod-toronto.ca"
        # Only load essential columns to save memory
        df = pd.read_csv(url, usecols=['latitude', 'longitude', '8hr_vehicle_volume', 'main_street', 'side_1_street', 'counting_date'])
        return clean(df)
    except:
        # Emergency Demo Data (Guaranteed to work)
        data = """counting_date,main_street,side_1_street,8hr_vehicle_volume,latitude,longitude
        2024-05-20,YONGE ST,DUNDAS ST,28000,43.6561,-79.3802
        2024-06-01,LAKE SHORE BLVD,BATHURST ST,35000,43.6356,-79.3995
        """
        return clean(pd.read_csv(io.StringIO(data)))

def clean(df):
    df = df.rename(columns={'latitude': 'lat', 'longitude': 'lng'})
    df['counting_date'] = pd.to_datetime(df['counting_date'], errors='coerce')
    return df.dropna(subset=['lat', 'lng'])

# --- 3. SIDEBAR & LOGIC ---
view = st.sidebar.radio("Navigation:", ["Traffic Map", "Road Notices"])
df = get_data()

if view == "Traffic Map":
    # Simple Filters
    q = st.sidebar.text_input("Search Street:").upper()
    v_min = st.sidebar.slider("Min Volume:", 0, 30000, 5000)
    
    mask = (df['8hr_vehicle_volume'] >= v_min)
    if q: mask &= (df['main_street'].str.contains(q, na=False))
    filtered = df[mask]

    # --- 4. THE MAP (NO TOKEN REQUIRED) ---
    st.pydeck_chart(pdk.Deck(
        # 'carto-light' style works without a Mapbox API key
        map_style='https://basemaps.cartocdn.com',
        initial_view_state=pdk.ViewState(latitude=43.6532, longitude=-79.3832, zoom=11, pitch=45),
        layers=[
            pdk.Layer(
                'ColumnLayer',
                data=filtered,
                get_position='[lng, lat]',
                get_elevation='8hr_vehicle_volume',
                elevation_scale=0.1,
                radius=100,
                get_fill_color=[227, 24, 55, 200], # Toronto Red
                pickable=True,
            ),
        ],
        tooltip={"text": "{main_street}\nVolume: {8hr_vehicle_volume}"}
    ))
    st.dataframe(filtered, use_container_width=True)

elif view == "Road Notices":
    st.subheader("🚧 Live Road Notices")
    try:
        r = requests.get("https://app.toronto.ca", timeout=5)
        st.write(pd.DataFrame(r.json().get('notices', []))[['road', 'description']])
    except:
        st.error("Toronto Data Portal is currently unreachable.")
    
