import streamlit as st
import pandas as pd
import requests
import pydeck as pdk
import io

# --- 1. CONFIG ---
st.set_page_config(page_title="Toronto Traffic Scope", layout="wide")
st.markdown("<style>.main-title { color: #E31837; font-weight: bold; font-size: 32px; }</style>", unsafe_allow_html=True)
st.markdown('<p class="main-title">🍁 Toronto Traffic Dashboard</p>', unsafe_allow_html=True)

# --- 2. DATA LOADING ---
@st.cache_data(ttl=3600)
def get_data():
    try:
        url = "https://ckan0.cf.opendata.inter.prod-toronto.ca"
        df = pd.read_csv(url)
        return clean(df)
    except:
        data = """counting_date,main_street,side_1_street,8hr_vehicle_volume,latitude,longitude
        2024-05-20,YONGE ST,DUNDAS ST,28000,43.6561,-79.3802
        2024-06-01,LAKE SHORE BLVD,BATHURST ST,35000,43.6356,-79.3995
        """
        return clean(pd.read_csv(io.StringIO(data)))

def clean(df):
    # Rename '8hr_vehicle_volume' to 'volume_8hr' to prevent PyDeck variable errors
    df = df.rename(columns={
        'latitude': 'lat', 
        'longitude': 'lng',
        '8hr_vehicle_volume': 'volume_8hr'
    })
    df['counting_date'] = pd.to_datetime(df['counting_date'], errors='coerce')
    # Filter out rows that might have non-numeric volume
    df['volume_8hr'] = pd.to_numeric(df['volume_8hr'], errors='coerce').fillna(0)
    return df.dropna(subset=['lat', 'lng'])

# --- 3. SIDEBAR ---
view = st.sidebar.radio("Navigation:", ["Traffic Map", "Road Notices"])
df = get_data()

if view == "Traffic Map":
    q = st.sidebar.text_input("Search Street:").upper()
    v_min = st.sidebar.slider("Min Volume:", 0, 35000, 5000)
    
    mask = (df['volume_8hr'] >= v_min)
    if q: mask &= (df['main_street'].str.contains(q, na=False))
    filtered = df[mask]

    # --- 4. THE MAP ---
    st.pydeck_chart(pdk.Deck(
        map_style='https://basemaps.cartocdn.com',
        initial_view_state=pdk.ViewState(latitude=43.6532, longitude=-79.3832, zoom=11, pitch=45),
        layers=[
            pdk.Layer(
                'ColumnLayer',
                data=filtered,
                get_position='[lng, lat]',
                get_elevation='volume_8hr', # Fixed name
                elevation_scale=0.1,
                radius=100,
                get_fill_color=[227, 24, 55, 200],
                pickable=True,
            ),
        ],
        tooltip={"text": "{main_street} & {side_1_street}\nVolume: {volume_8hr}"}
    ))
    st.dataframe(filtered, use_container_width=True)

elif view == "Road Notices":
    st.subheader("🚧 Live Road Notices")
    try:
        r = requests.get("https://app.toronto.ca", timeout=5)
        st.write(pd.DataFrame(r.json().get('notices', []))[['road', 'description']])
    except:
        st.error("Toronto Data Portal is currently unreachable.")
    
