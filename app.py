import streamlit as st
import pandas as pd
import requests
import pydeck as pdk
import io

# --- 1. APP CONFIGURATION ---
st.set_page_config(page_title="Toronto Traffic Scope", layout="wide", page_icon="🍁")

st.markdown("""
    <style>
    .main-title { font-size: 38px; font-weight: bold; color: #E31837; }
    .subtitle { font-size: 18px; color: #555; }
    </style>
    """, unsafe_allow_html=True)

st.markdown('<p class="main-title">🍁 Toronto Traffic Data Dashboard</p>', unsafe_allow_html=True)
st.markdown('<p class="subtitle">Official Traffic Volumes & Live Road Restrictions</p>', unsafe_allow_html=True)

# --- 2. DATA FETCHING ---
@st.cache_data
def get_traffic_volumes():
    try:
        # Stable City of Toronto CSV link
        url = "https://ckan0.cf.opendata.inter.prod-toronto.ca"
        df = pd.read_csv(url)
        return clean_volume_data(df)
    except:
        # Demo Fallback
        data = """counting_date,main_street,side_1_street,8hr_vehicle_volume,lat,lng,ward_name
        2024-05-20,YONGE ST,DUNDAS ST,28000,43.6561,-79.3802,Toronto Centre
        2024-06-01,LAKE SHORE BLVD,BATHURST ST,35000,43.6356,-79.3995,Spadina-Fort York
        """
        return clean_volume_data(pd.read_csv(io.StringIO(data)))

def clean_volume_data(df):
    df = df.rename(columns={'latitude': 'lat', 'Latitude': 'lat', 'longitude': 'lng', 'Longitude': 'lng'})
    if '8hr_vehicle_volume' not in df.columns:
        vol_cols = [c for c in df.columns if 'volume' in c.lower()]
        df['8hr_vehicle_volume'] = df[vol_cols[0]] if vol_cols else 1000
    df['counting_date'] = pd.to_datetime(df['counting_date'], errors='coerce')
    return df.dropna(subset=['lat', 'lng'])

# --- 3. SIDEBAR ---
view_option = st.sidebar.radio("View:", ["Intersection Volumes", "Live Road Restrictions"])
df_vol = get_traffic_volumes()

if view_option == "Intersection Volumes":
    st.sidebar.subheader("🔍 Filters")
    search_query = st.sidebar.text_input("Street Search:", "").upper()
    
    # Filter Logic
    mask = (df_vol['8hr_vehicle_volume'] >= st.sidebar.slider("Min Volume", 0, 20000, 5000))
    if search_query:
        mask &= (df_vol['main_street'].str.contains(search_query, na=False))
    filtered = df_vol[mask]

    # --- 4. MAP (FIXED) ---
    # Attempt to get token from Secrets; fallback to None
    mapbox_token = st.secrets.get("MAPBOX_TOKEN", None)
    
    st.pydeck_chart(pdk.Deck(
        map_style='mapbox://styles/mapbox/streets-v11' if mapbox_token else 'light',
        api_keys={'mapbox': mapbox_token} if mapbox_token else None,
        initial_view_state=pdk.ViewState(latitude=43.6532, longitude=-79.3832, zoom=12, pitch=45),
        layers=[
            pdk.Layer(
                'ColumnLayer',
                data=filtered,
                get_position='[lng, lat]',
                get_elevation='8hr_vehicle_volume',
                elevation_scale=0.1,
                radius=80,
                get_fill_color=[227, 24, 55, 200], # Explicit RGBA list
                pickable=True,
            ),
        ],
        tooltip={"text": "{main_street} & {side_1_street}\nVol: {8hr_vehicle_volume}"}
    ))

elif view_option == "Live Road Restrictions":
    st.subheader("🚧 Live Road Notices")
    try:
        r = requests.get("https://app.toronto.ca", timeout=10)
        st.dataframe(pd.DataFrame(r.json().get('notices', [])))
    except:
        st.error("Could not load live data.")
    
