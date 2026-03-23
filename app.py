import streamlit as st
import pandas as pd
import plotly.express as px

# 1. Page Configuration
st.set_page_config(page_title="Toronto Traffic Dashboard", page_icon="🍁", layout="wide")

# 2. Fixed Data Loading Function
@st.cache_data
def load_data():
    # URL for Toronto's Open Data (Intersection Traffic Volumes 1984-Present)
    # Note: Replace this with your specific CSV path if hosting locally
    url = "https://raw.githubusercontent.com"
    
    try:
        # FIX: 'on_bad_lines' skips errors like the one on line 13
        # FIX: 'engine=python' handles varied delimiters more reliably
        df = pd.read_csv(url, on_bad_lines='skip', engine='python')
        
        # Simple data cleaning: Ensure Year is an integer
        if 'count_date' in df.columns:
            df['Year'] = pd.to_datetime(df['count_date']).dt.year
        return df
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return None

# 3. Main App UI
st.title("🍁 Toronto Traffic Dashboard (1984-Present)")

data = load_data()

if data is not None:
    # Sidebar Filters
    st.sidebar.header("Filter Options")
    year_range = st.sidebar.slider("Select Year Range", 
                                   int(data['Year'].min()), 
                                   int(data['Year'].max()), 
                                   (2010, 2024))
    
    # Filtered Data
    filtered_data = data[(data['Year'] >= year_range[0]) & (data['Year'] <= year_range[1])]

    # Metrics Row
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Records", len(filtered_data))
    col2.metric("Start Year", year_range[0])
    col3.metric("End Year", year_range[1])

    # Visualizations
    st.subheader("Traffic Volume Trends")
    if 'v_total' in filtered_data.columns:
        fig = px.line(filtered_data.groupby('Year')['v_total'].sum().reset_index(), 
                      x='Year', y='v_total', title="Total Traffic Volume Over Time")
        st.plotly_chart(fig, use_container_width=True)
    
    st.subheader("Raw Data Preview")
    st.dataframe(filtered_data.head(100))
else:
    st.info("Please ensure your data source URL is valid or upload a local CSV.")

