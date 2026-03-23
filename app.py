import streamlit as st
import pandas as pd
import requests
import pydeck as pdk

# --- APP CONFIGURATION ---
st.set_page_config(page_title="Toronto Traffic Scope", layout="wide")
st.title("🍁 Toronto Traffic Data Dashboard")
st.markdown("Digitally visualize official traffic reports and road restrictions from the City of Toronto.")

# --- DATA FETCHING FUNCTIONS ---
@st.cache_data
def get_traffic_volumes():
    """Fetches the most recent Traffic Volume Summary from Toronto Open Data."""
    # 1. Get Package Metadata to find the CSV URL
    base_url = "https://ckan0.cf.opendata.inter.prod-toronto.ca"
    package_id = "traffic-volumes-at-intersections-for-all-modes"
    
    try:
        # Fetch package metadata
        url = f"{base_url}/package_show"
        params = {"id": package_id}
        response = requests.get(url, params=params).json()
        
        # Find the resource for 'Most Recent Summary Data'
        resources = response["result"]["resources"]
        resource_url = None
        for res in resources:
            if "most_recent_summary" in res["name"].lower() and res["format"].lower() == "csv":
                resource_url = res["url"]
                break
        
        if not resource_url:
            st.error("Could not locate the specific traffic volume CSV.")
            return None
            
        # 2. Load the CSV Data
        df = pd.read_csv(resource_url)
        
        # Clean/Rename columns for mapping if necessary (ensure lat/lon exist)
        # The dataset typically uses 'lat' and 'lng' or similar. 
        # We'll drop rows with missing coordinates.
        if 'lat' in df.columns and 'lng' in df.columns:
            df = df.dropna(subset=['lat', 'lng'])
        
        return df
        
    except Exception as e:
        st.error(f"Error fetching Traffic Volume data: {e}")
        return None

@st.cache_data
def get_road_restrictions():
    """Fetches live road restrictions (JSON endpoint)."""
    # URL found in Open Data documentation for live restrictions
    url = "https://secure.toronto.ca" 
    try:
        response = requests.get(url).json()
        # The JSON structure usually contains a list of notices
        if 'notices' in response:
            df = pd.DataFrame(response['notices'])
            # Extract lat/lon if nested or format appropriately
            # Note: Real-time JSON structures can vary; this is a generalized parser
            return df
        return pd.DataFrame()
    except Exception as e:
        # Fallback or specific error handling
        return pd.DataFrame()

# --- SIDEBAR CONTROLS ---
st.sidebar.header("Data Controls")
view_option = st.sidebar.radio("Select Report Type:", ["Intersection Volumes", "Live Road Restrictions"])

# --- MAIN INTERFACE ---

if view_option == "Intersection Volumes":
    st.subheader("🚦 Intersection Traffic Volumes")
    with st.spinner("Fetching latest official data..."):
        df_vol = get_traffic_volumes()
    
    if df_vol is not None and not df_vol.empty:
        # Show top intersections by 8-hour volume
        # Assuming column 'ph_8hr_vehicle_volume' exists based on standard schema
        if '8hr_vehicle_volume' in df_vol.columns:
            vol_col = '8hr_vehicle_volume'
        else:
            # Fallback to finding a numeric column if schema changed
            vol_col = df_vol.select_dtypes(include=['number']).columns[0]

        # Filter visuals
        min_vol = st.sidebar.slider("Minimum Volume Filter", 0, int(df_vol[vol_col].max()), 5000)
        filtered_df = df_vol[df_vol[vol_col] >= min_vol]
        
        st.metric("Intersections Monitored", len(filtered_df))
        
        # Map Visualization
        st.pydeck_chart(pdk.Deck(
            map_style='mapbox://styles/mapbox/light-v9',
            initial_view_state=pdk.ViewState(
                latitude=43.70,
                longitude=-79.42,
                zoom=10,
                pitch=50,
            ),
            layers=[
                pdk.Layer(
                    'ColumnLayer',
                    data=filtered_df,
                    get_position='[lng, lat]',
                    get_elevation=vol_col,
                    elevation_scale=0.5,
                    radius=100,
                    get_fill_color='[255, 165, 0, 160]',
                    pickable=True,
                    auto_highlight=True,
                ),
            ],
            tooltip={"text": "{main_street} & {side_1_street}\nVolume: {" + vol_col + "}"}
        ))
        
        st.dataframe(filtered_df[['main_street', 'side_1_street', vol_col, 'counting_date']].sort_values(vol_col, ascending=False))
    else:
        st.warning("Data unavailable. The Open Data API might be down or schema changed.")

elif view_option == "Live Road Restrictions":
    st.subheader("🚧 Live Road Restrictions & Closures")
    st.info("This module connects to the City's real-time notices feed.")
    
    df_rest = get_road_restrictions()
    
    if not df_rest.empty:
        # Display list of closures
        # Only show active columns
        display_cols = [col for col in ['road', 'description', 'start_date', 'end_date'] if col in df_rest.columns]
        st.dataframe(df_rest[display_cols])
    else:
        st.write("No active road restriction data found or API format incompatible.")

