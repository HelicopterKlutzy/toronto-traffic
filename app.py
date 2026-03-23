import streamlit as st
import pandas as pd
import requests
import pydeck as pdk
import re

# --- APP CONFIGURATION ---
st.set_page_config(page_title="Toronto Traffic Scope", layout="wide")
st.title("🍁 Toronto Traffic Data Dashboard")
st.markdown("Digitally visualize official traffic reports and road restrictions from the City of Toronto.")

# --- ROBUST DATA FETCHING ---
@st.cache_data
def get_traffic_volumes():
    """
    Fetches traffic data with a 'Double-Barrel' strategy to prevent errors.
    Strategy 1: Direct API (ckan0)
    Strategy 2: Web Scrape (open.toronto.ca)
    """
    status_placeholder = st.empty()
    status_placeholder.info("Attempting to connect to City Data Services...")

    # --- STRATEGY 1: DIRECT API ACCESS ---
    api_url = "https://ckan0.cf.opendata.inter.prod-toronto.ca/api/3/action/package_show"
    params = {"id": "traffic-volumes-at-intersections-for-all-modes"}
    # 'User-Agent' is CRITICAL. It tells the server we are a browser, not a bot.
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}

    csv_url = None

    try:
        r = requests.get(api_url, params=params, headers=headers)
        if r.status_code == 200:
            data = r.json()
            resources = data["result"]["resources"]
            # Find the most recent summary CSV
            for res in resources:
                if "most_recent_summary" in res["name"].lower() and res["format"].lower() == "csv":
                    csv_url = res["url"]
                    break
    except Exception:
        pass # API failed, move silently to Strategy 2

    # --- STRATEGY 2: WEB SCRAPE (FALLBACK) ---
    if not csv_url:
        status_placeholder.warning("API blocked. Switching to backup scraping method...")
        try:
            page_url = "https://open.toronto.ca/dataset/traffic-volumes-at-intersections-for-all-modes/"
            r_page = requests.get(page_url, headers=headers)
            # Look for the specific resource link in the HTML
            # Matches: href=".../download/..." followed closely by .csv check
            links = re.findall(r'href="(https://ckan0[^"]+)"', r_page.text)
            for link in links:
                if "most_recent_summary" in link.lower() or "tmc_most_recent" in link.lower():
                    csv_url = link
                    break
        except Exception as e:
            st.error(f"Backup method failed: {e}")
            return None

    # --- LOAD DATA ---
    if csv_url:
        status_placeholder.success(f"Data Source Found! Loading...")
        try:
            df = pd.read_csv(csv_url, on_bad_lines='skip')
            
            # Standardize Coordinate Columns
            col_map = {
                'latitude': 'lat', 'Latitude': 'lat',
                'longitude': 'lng', 'Longitude': 'lng'
            }
            df = df.rename(columns=col_map)
            
            # Clean Coordinates
            if 'lat' in df.columns and 'lng' in df.columns:
                df = df.dropna(subset=['lat', 'lng'])
                status_placeholder.empty() # Clear status messages
                return df
            else:
                st.error("Data loaded but GPS coordinates are missing.")
                return None
        except Exception as e:
            st.error(f"Failed to read CSV: {e}")
            return None
    else:
        st.error("Could not locate data file via API or Website. The City may have moved the dataset.")
        return None

@st.cache_data
def get_road_restrictions():
    """Fetches live road restrictions."""
    url = "https://secure.toronto.ca" 
    try:
        response = requests.get(url).json()
        if 'notices' in response:
            return pd.DataFrame(response['notices'])
        return pd.DataFrame()
    except:
        return pd.DataFrame()

# --- MAIN INTERFACE ---
view_option = st.sidebar.radio("Select Report Type:", ["Intersection Volumes", "Live Road Restrictions"])

if view_option == "Intersection Volumes":
    st.subheader("🚦 Intersection Traffic Volumes")
    
    df_vol = get_traffic_volumes()
    
    if df_vol is not None and not df_vol.empty:
        # Identify volume column
        vol_col = '8hr_vehicle_volume' if '8hr_vehicle_volume' in df_vol.columns else df_vol.select_dtypes(include=['number']).columns[0]

        # Sidebar Filter
        max_val = int(df_vol[vol_col].max())
        min_vol = st.sidebar.slider("Minimum Traffic Volume", 0, max_val, 5000)
        filtered_df = df_vol[df_vol[vol_col] >= min_vol]
        
        # Map
        st.pydeck_chart(pdk.Deck(
            map_style='mapbox://styles/mapbox/light-v9',
            initial_view_state=pdk.ViewState(
                latitude=43.70, longitude=-79.42, zoom=10, pitch=50,
            ),
            layers=[
                pdk.Layer(
                    'ColumnLayer',
                    data=filtered_df,
                    get_position='[lng, lat]',
                    get_elevation=vol_col,
                    elevation_scale=0.5,
                    radius=100,
                    get_fill_color=[200, 30, 0, 160],
                    pickable=True,
                ),
            ],
            tooltip={"text": "{main_street} / {side_1_street}\nVolume: " + f"{{{vol_col}}}"}
        ))
        st.write(f"Showing {len(filtered_df)} high-volume intersections.")
        st.dataframe(filtered_df.head(50))

elif view_option == "Live Road Restrictions":
    st.subheader("🚧 Live Road Restrictions")
    df_rest = get_road_restrictions()
    if not df_rest.empty:
        st.dataframe(df_rest[['road', 'description', 'start_date', 'end_date']].dropna())
    else:
        st.write("No active road restriction data found.")
    
