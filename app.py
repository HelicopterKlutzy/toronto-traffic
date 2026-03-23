import streamlit as st
import pandas as pd
import requests

@st.cache_data
def load_data_safe():
    # Package ID for Turning Movement Counts
    package_id = "traffic-volumes-at-intersections-for-all-modes"
    base_url = f"https://ckan0.cf.opendata.inter.prod-toronto.ca{package_id}"
    
    try:
        response = requests.get(base_url)
        # Check if the server actually returned a success code
        if response.status_code != 200:
            st.error(f"API Error: Server returned status {response.status_code}")
            return pd.DataFrame()
            
        data = response.json()
        
        # Find the 'TMC Summary Data' resource
        resource_id = None
        for resource in data["result"]["resources"]:
            if "summary" in resource["name"].lower() and resource["format"].lower() == "csv":
                resource_id = resource["id"]
                break
        
        if not resource_id:
            st.error("Could not find the summary CSV in the dataset metadata.")
            return pd.DataFrame()

        # Direct CSV download bypasses JSON parsing errors for large files
        csv_url = f"https://ckan0.cf.opendata.inter.prod-toronto.ca{resource_id}"
        df = pd.read_csv(csv_url)
        
        # Basic cleaning
        df['count_date'] = pd.to_datetime(df['count_date'])
        df['year'] = df['count_date'].dt.year
        return df

    except requests.exceptions.JSONDecodeError:
        st.error("The API returned an empty or invalid response (likely an HTML error page).")
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Unexpected error: {e}")
        return pd.DataFrame()

# Use the function
df = load_data_safe()
if not df.empty:
    st.write("Data loaded successfully!")
    st.dataframe(df.head())
    
