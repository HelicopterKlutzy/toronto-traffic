import streamlit as st
import pandas as pd
import plotly.express as px
import requests

# 1. Setup Page
st.set_page_config(page_title="Toronto Traffic Explorer", layout="wide")
st.title("🚦 Toronto Traffic: Automated Data Comparison")

@st.cache_data
def load_data_from_api():
    # Toronto Open Data API endpoint for TMC Summary Data
    # Dataset: https://open.toronto.ca/dataset/traffic-volumes-at-intersections-for-all-modes/
    base_url = "https://ckan0.cf.opendata.inter.prod-toronto.ca"
    params = { "id": "traffic-volumes-at-intersections-for-all-modes"}
    
    # 1. Get package metadata to find the specific CSV resource
    package = requests.get(base_url, params=params).json()
    
    # 2. Locate the summary data CSV (usually contains 'summary' in the name)
    resource_id = None
    for resource in package["result"]["resources"]:
        if "summary" in resource["name"].lower() and resource["format"].lower() == "csv":
            resource_id = resource["id"]
            break
    
    if not resource_id:
        st.error("Could not find the summary CSV resource.")
        return pd.DataFrame()

    # 3. Construct direct download URL and load into Pandas
    download_url = f"https://ckan0.cf.opendata.inter.prod-toronto.ca{resource_id}"
    df = pd.read_csv(download_url)
    
    # Data Cleaning
    df['count_date'] = pd.to_datetime(df['count_date'])
    df['year'] = df['count_date'].dt.year
    return df

# Main App Logic
try:
    df = load_data_from_api()
    if not df.empty:
        # (Insert your sidebar filters and plotting logic here as before)
        st.success("Data successfully fetched from Toronto Open Data API!")
        st.write(df.head())
except Exception as e:
    st.error(f"Failed to fetch data: {e}")
    
