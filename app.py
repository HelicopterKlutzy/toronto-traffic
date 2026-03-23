import streamlit as st
import pandas as pd
import requests
import pydeck as pdk
import io

# --- 1. APP SETUP ---
st.set_page_config(page_title="Toronto Traffic Dashboard", layout="wide")
st.markdown("<style>.title { color: #E31837; font-weight: bold; font-size: 30px; }</style>", unsafe_allow_html=True)
st.markdown('<p class="title">🍁 Toronto Traffic Dashboard (1984-Present)</p>', unsafe_allow_html=True)

# --- 2. DATA LOADING & CLEANING ---
@st.cache_data(ttl=86400)
def get_full_data():
    """Fetches the full dataset and renames problematic columns."""
    try:
        url = "https://ckan0.cf.opendata.inter.prod-toronto.ca"
        df = pd.read_csv(url)
        
        # FIX: Rename the '8hr...' column so PyDeck doesn't crash
        df = df.rename(columns={
            'latitude': 'lat', 
            'longitude': 'lng',
            '8hr_vehicle_volume': 'volume_8hr'
        })
        
        # Clean and convert data types
        df['counting_date'] = pd.to_datetime(df['counting_date'], errors='coerce')
        df['volume_8hr'] = pd.to_numeric(df['volume_8hr'], errors='coerce').fillna(0)
        
        return df.dropna(subset=['lat', 'lng', 'counting_date'])
    except Exception as e:
        st.error(f"Data loading error: {e}")
        return pd.DataFrame()

# --- 3. SIDEBAR & FILTERS ---
df = get_full_data()

if not df.empty:
    st.sidebar.header("Filter Results")
    
    # Text Search
    search = st.sidebar.text_input("Search Intersection:", "").upper()
    
    # Date Range Slider
    min_d, max_d = df['counting_date'].min().date(), df['counting_date'].max().date()
    start_d, end_d = st.sidebar.slider("Select Date Range:", min_d, max_d, (min_d, max_d))
    
    # Volume Slider
    min_v = st.sidebar.slider("Minimum Volume:", 0, 35000, 5000)

    # Filter Logic
    mask = (df['counting_date'].dt.date >= start_d) & \
           (df['counting_date'].dt.date <= end_d) & \
           (df['volume_8hr'] >= min_v)
    
    if search:
        mask &= (df['main_street'].str.contains(search, na=False) | 
                 df['side_1_street'].str.contains(search, na=False))
    
    filtered = df[mask]

    # --- 4. MAP VISUALIZATION ---
    st.write(f"Displaying **{len(filtered):,}** records from **{start_d} to {end_d}**")

    st.pydeck_chart(pdk.Deck(
        map_style='https://basemaps.cartocdn.com',
        initial_view_state=pdk.ViewState(latitude=43.66, longitude=-79.38, zoom=11, pitch=40),
        layers=[
            pdk.Layer(
                'ColumnLayer',
                data=filtered,
                get_position='[lng, lat]',
                get_elevation='volume_8hr', # Uses fixed variable name
                elevation_scale=0.08,
                radius=100,
                get_fill_color=[227, 24, 55, 180], # RGBA Toronto Red
                pickable=True,
            ),
        ],
        tooltip={"text": "{main_street} & {side_1_street}\nDate: {counting_date}\nVolume: {volume_8hr}"}
    ))

    # Raw Data Expander
    with st.expander("View Filtered Data Table"):
        st.dataframe(filtered.sort_values('counting_date', ascending=False), use_container_width=True)
else:
    st.info("Loading Toronto's historical traffic database... please wait.")
    
