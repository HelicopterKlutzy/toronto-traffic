import streamlit as st
import pandas as pd
import requests
import pydeck as pdk
import io

# --- 1. PAGE SETUP ---
st.set_page_config(page_title="Toronto Traffic: Full History", layout="wide")
st.markdown("<style>.main-title { color: #E31837; font-weight: bold; font-size: 32px; }</style>", unsafe_allow_html=True)
st.markdown('<p class="main-title">🍁 Toronto Traffic: 1984 - Present</p>', unsafe_allow_html=True)

# --- 2. FETCH FULL DATASET ---
@st.cache_data(ttl=86400) # Cache for 24 hours
def get_full_history():
    """Fetches the complete summary of all intersection counts since 1984."""
    try:
        # Link to the official 'Traffic Volumes at Intersections' full summary CSV
        url = "https://ckan0.cf.opendata.inter.prod-toronto.ca"
        df = pd.read_csv(url)
        
        # 1. Fix the "8h" error by renaming the column immediately
        df = df.rename(columns={
            'latitude': 'lat', 
            'longitude': 'lng',
            '8hr_vehicle_volume': 'volume_8hr'
        })
        
        # 2. Clean and convert dates
        df['counting_date'] = pd.to_datetime(df['counting_date'], errors='coerce')
        df['volume_8hr'] = pd.to_numeric(df['volume_8hr'], errors='coerce').fillna(0)
        
        return df.dropna(subset=['lat', 'lng', 'counting_date'])
    except Exception as e:
        st.error(f"Error loading full dataset: {e}")
        return pd.DataFrame()

# --- 3. SIDEBAR FILTERS ---
df = get_full_history()

if not df.empty:
    st.sidebar.header("Explore History")
    
    # Street Search
    q = st.sidebar.text_input("Search Intersection:", placeholder="e.g. YONGE").upper()
    
    # FULL Date Range Slider
    min_date = df['counting_date'].min().date()
    max_date = df['counting_date'].max().date()
    date_range = st.sidebar.slider("Select Years:", min_date, max_date, (min_date, max_date))
    
    # Volume Filter
    v_min = st.sidebar.number_input("Minimum 8-Hour Volume:", value=1000, step=500)

    # --- 4. FILTERING LOGIC ---
    mask = (df['counting_date'].dt.date >= date_range[0]) & \
           (df['counting_date'].dt.date <= date_range[1]) & \
           (df['volume_8hr'] >= v_min)
    
    if q:
        mask &= (df['main_street'].str.contains(q, na=False) | 
                 df['side_1_street'].str.contains(q, na=False))
    
    filtered = df[mask]

    # --- 5. VISUALIZATION ---
    st.write(f"Showing **{len(filtered):,}** intersection records from **{date_range[0].year} to {date_range[1].year}**.")

    st.pydeck_chart(pdk.Deck(
        map_style='https://basemaps.cartocdn.com',
        initial_view_state=pdk.ViewState(latitude=43.66, longitude=-79.38, zoom=11, pitch=40),
        layers=[
            pdk.Layer(
                'ColumnLayer',
                data=filtered,
                get_position='[lng, lat]',
                get_elevation='volume_8hr',
                elevation_scale=0.05, # Scaled down for high-volume counts
                radius=120,
                get_fill_color=,
                pickable=True,
            ),
        ],
        tooltip={"text": "{main_street} & {side_1_street}\nDate: {counting_date}\nVolume: {volume_8hr}"}
    ))

    # Detailed Table
    with st.expander("📊 View All Results Table"):
        st.dataframe(filtered.sort_values('counting_date', ascending=False), use_container_width=True)
else:
    st.warning("Wait a moment... downloading the full 1984-2024 dataset from the City portal.")
    
