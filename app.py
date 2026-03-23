import streamlit as st
import pandas as pd
import requests
import pydeck as pdk
import re

# --- APP CONFIGURATION ---
st.set_page_config(page_title="Toronto Traffic Scope", layout="wide", page_icon="🍁")
st.title("🍁 Toronto Traffic Data Dashboard")
st.markdown("Digitally visualize official traffic reports and road restrictions from the City of Toronto.")

# --- ROBUST DATA FETCHING ---
@st.cache_data
def get_traffic_volumes():
    """
    Fetches traffic data with a 'Double-Barrel' strategy to prevent 404 errors.
    Strategy 1: Direct API (ckan0)
    Strategy 2: Web Scrape (open.toronto.ca)
    """
    status_placeholder = st.empty()
    status_placeholder.info("Attempting to connect to City Data Services...")

    # --- STRATEGY 1: DIRECT API ACCESS ---
    api_url = "https://ckan0.cf.opendata.inter.prod-toronto.ca"
    params = {"id": "traffic-volumes-at-intersections-for-all-modes"}
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}

    csv_url = None

    try:
        r = requests.get(api_url, params=params, headers=headers, timeout=10)
        if r.status_code == 200:
            data = r.json()
            resources = data["result"]["resources"]
            for res in resources:
                if "most_recent_summary" in res["name"].lower() and res["format"].lower() == "csv":
                    csv_url = res["url"]
                    break
    except Exception:
        pass 

    # --- STRATEGY 2: WEB SCRAPE (FALLBACK) ---
    if not csv_url:
        status_placeholder.warning("API blocked. Switching to backup scraping method...")
        try:
            page_url = "https://open.toronto.ca"
            r_page = requests.get(page_url, headers=headers, timeout=10)
            links = re.findall(r'href="(https://ckan0[^"]+)"', r_page.text)
            for link in links:
                if "most_recent_summary" in link.lower() or "tmc_most_recent" in link.lower():
                    csv_url = link
                    break
        except Exception as e:
            st.error(f"Backup method failed: {e}")
            return None

    # --- LOAD AND CLEAN DATA ---
    if csv_url:
        status_placeholder.success(f"Data Source Found! Cleaning records...")
        try:
            df = pd.read_csv(csv_url, on_bad_lines='skip')
            
            # Standardize Coordinates
            col_map = {'latitude': 'lat', 'Latitude': 'lat', 'longitude': 'lng', 'Longitude': 'lng'}
            df = df.rename(columns=col_map)
            
            # Convert Date to Real Date Object
            if 'counting_date' in df.columns:
                df['counting_date'] = pd.to_datetime(df['counting_date'], errors='coerce')
                df = df.dropna(subset=['counting_date'])
                # Sort NEWEST first
                df = df.sort_values(by='counting_date', ascending=False)
            
            # Clean GPS Data
            if 'lat' in df.columns and 'lng' in df.columns:
                df = df.dropna(subset=['lat', 'lng'])
                status_placeholder.empty()
                return df
            else:
                st.error("Data loaded but GPS coordinates are missing.")
                return None
        except Exception as e:
            st.error(f"Failed to read CSV: {e}")
            return None
    else:
        st.error("Could not locate data file. The City may have moved the dataset.")
        return None

@st.cache_data
def get_road_restrictions():
    """Fetches live road restrictions."""
    url = "https://secure.toronto.ca" 
    try:
        response = requests.get(url, timeout=10).json()
        if 'notices' in response:
            return pd.DataFrame(response['notices'])
        return pd.DataFrame()
    except:
        return pd.DataFrame()

# --- SIDEBAR CONTROLS ---
st.sidebar.header("App Controls")
view_option = st.sidebar.radio("Select Report Type:", ["Intersection Volumes", "Live Road Restrictions"])

# --- MAIN INTERFACE ---

if view_option == "Intersection Volumes":
    st.subheader("🚦 Intersection Traffic Volumes (Vehicle Counts)")
    
    df_vol = get_traffic_volumes()
    
    if df_vol is not None and not df_vol.empty:
        # Dynamic volume column check
        vol_col = '8hr_vehicle_volume' if '8hr_vehicle_volume' in df_vol.columns else df_vol.select_dtypes(include=['number']).columns[0]

        # --- FILTERS ---
        st.sidebar.markdown("---")
        st.sidebar.subheader("Filters")
        
        # Year Filter (Fixes the 2014 issue)
        min_year = int(df_vol['counting_date'].dt.year.min())
        max_year = int(df_vol['counting_date'].dt.year.max())
        selected_year = st.sidebar.slider("Show data from (Year):", min_year, max_year, 2018)

        # Volume Filter
        max_val = int(df_vol[vol_col].max())
        min_vol = st.sidebar.slider("Minimum Traffic Volume:", 0, max_val, 10000)

        # Apply Filters
        mask = (df_vol['counting_date'].dt.year >= selected_year) & (df_vol[vol_col] >= min_vol)
        filtered_df = df_vol[mask]
        
        # Statistics
        c1, c2, c3 = st.columns(3)
        c1.metric("Intersections Shown", len(filtered_df))
        c2.metric("Newest Record", filtered_df['counting_date'].dt.year.max())
        c3.metric("Highest Volume", f"{int(filtered_df[vol_col].max()):,}")

        # --- VISUALIZATION ---
        if not filtered_df.empty:
            st.pydeck_chart(pdk.Deck(
                map_style='mapbox://styles/mapbox/light-v9',
                initial_view_state=pdk.ViewState(
                    latitude=43.70, longitude=-79.42, zoom=10.5, pitch=45,
                ),
                layers=[
                    pdk.Layer(
                        'ColumnLayer',
                        data=filtered_df,
                        get_position='[lng, lat]',
                        get_elevation=vol_col,
                        elevation_scale=0.4,
                        radius=120,
                        get_fill_color='', # Toronto Orange
                        pickable=True,
                        auto_highlight=True,
                    ),
                ],
                tooltip={"text": "{main_street} / {side_1_street}\nCounted: {counting_date}\nVolume: " + f"{{{vol_col}}}"}
            ))
            
            st.markdown("### 📊 Raw Data (Sorted by Newest)")
            display_cols = ['counting_date', 'main_street', 'side_1_street', vol_col]
            st.dataframe(filtered_df[display_cols].head(100), hide_index=True, use_container_width=True)
        else:
            st.warning("No data matches your filters. Try lowering the Year or Volume requirements.")

elif view_option == "Live Road Restrictions":
    st.subheader("🚧 Live Road Restrictions & Closures")
    st.info("Showing real-time construction and closure notices.")
    
    df_rest = get_road_restrictions()
    
    if not df_rest.empty:
        # Display list of closures
        display_cols = [col for col in ['road', 'description', 'start_date', 'end_date'] if col in df_rest.columns]
        st.dataframe(df_rest[display_cols].dropna(), use_container_width=True)
    else:
        st.write("No active road restriction data found right now.")
            
