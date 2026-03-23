import streamlit as st
import pandas as pd
import plotly.express as px

# 1. Setup Page
st.set_page_config(page_title="Toronto Traffic Dashboard", layout="wide")
st.title("🚦 Toronto Traffic Intersection Comparison")

# --- NEW: Uploader is now in the center of the page, not the sidebar ---
st.info("The automated link may be down. Please download 'tmc_summary_data.csv' from Toronto Open Data and upload it below.")
uploaded_file = st.file_uploader("Upload 'tmc_summary_data.csv' here", type="csv")

@st.cache_data
def load_data(file):
    try:
        # Load and clean data
        df = pd.read_csv(file, on_bad_lines='skip', engine='python')
        
        # Smart column detection (finding 'date', 'v_tot', 'p_tot')
        cols = {c.lower().strip(): c for c in df.columns}
        date_key = next((v for k, v in cols.items() if 'date' in k), None)
        v_key = next((v for k, v in cols.items() if 'v_tot' in k or 'veh' in k), None)
        p_key = next((v for k, v in cols.items() if 'p_tot' in k or 'ped' in k), None)
        main_key = next((v for k, v in cols.items() if 'main' in k), 'main')
        cross_key = next((v for k, v in cols.items() if 'cross' in k), 'cross_st')

        if not date_key:
            st.error(f"Date column not found. Available columns: {list(df.columns)}")
            return pd.DataFrame()

        # Cleaning
        df[date_key] = pd.to_datetime(df[date_key], errors='coerce')
        df = df.dropna(subset=[date_key])
        df['year'] = df[date_key].dt.year.astype(int)
        df['intersection'] = df[main_key].astype(str) + " & " + df[cross_key].astype(str)
        
        # Rename for consistency
        df = df.rename(columns={v_key: 'Vehicles', p_key: 'Pedestrians'})
        return df[['year', 'intersection', 'Vehicles', 'Pedestrians']]
    except Exception as e:
        st.error(f"Error reading file: {e}")
        return pd.DataFrame()

# 2. Main App Logic
if uploaded_file:
    df = load_data(uploaded_file)
    
    if not df.empty:
        # Show filters in the sidebar ONLY after file is uploaded
        st.sidebar.header("Chart Filters")
        intersections = sorted(df['intersection'].unique())
        selected = st.sidebar.multiselect("Select Intersections", intersections, default=intersections[:1])
        
        min_y, max_y = int(df['year'].min()), int(df['year'].max())
        years = st.sidebar.slider("Year Range", min_y, max_y, (min_y, max_y))
        
        # Filtering
        filtered = df[(df['intersection'].isin(selected)) & (df['year'].between(*years))]
        
        if not filtered.empty:
            grouped = filtered.groupby(['year', 'intersection']).sum().reset_index()
            
            tab1, tab2 = st.tabs(["🚗 Vehicles", "🚶 Pedestrians"])
            with tab1:
                st.plotly_chart(px.line(grouped, x='year', y='Vehicles', color='intersection', markers=True))
            with tab2:
                st.plotly_chart(px.bar(grouped, x='year', y='Pedestrians', color='intersection', barmode='group'))
        else:
            st.warning("Adjust your sidebar filters to see data.")
else:
    st.warning("Awaiting file upload...")
    
