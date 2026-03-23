import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Toronto Traffic Fix", layout="wide")
st.title("🚦 Toronto Traffic Intersection Comparison")

uploaded_file = st.file_uploader("Upload 'tmc_summary_data.csv' here", type="csv")

@st.cache_data
def load_data(file):
    try:
        # Load and clean headers
        df = pd.read_csv(file, on_bad_lines='skip', engine='python')
        df.columns = [str(c).strip().lower() for c in df.columns]
        
        # --- ROBUST COLUMN SEARCH ---
        # Instead of 'main', we look for any column containing 'main' or 'location'
        date_col = next((c for c in df.columns if 'date' in c), None)
        v_col = next((c for c in df.columns if 'v_tot' in c or 'veh' in c), None)
        p_col = next((c for c in df.columns if 'p_tot' in c or 'ped' in c), None)
        main_col = next((c for c in df.columns if 'main' in c or 'location' in c), None)
        cross_col = next((c for c in df.columns if 'cross' in c or 'x_st' in c), None)

        # Fail-safe check
        if not all([date_col, main_col, v_col]):
            st.error(f"Missing required columns! Found: {list(df.columns)}")
            st.info("Ensure you are uploading the 'TMC Summary Data' file.")
            return pd.DataFrame()

        # Cleaning
        df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
        df = df.dropna(subset=[date_col])
        df['year'] = df[date_col].dt.year.astype(int)
        
        # Combine names safely
        df['intersection'] = df[main_col].astype(str) + " & " + df[cross_col].fillna('N/A').astype(str)
        
        # Rename for simplicity
        df = df.rename(columns={v_col: 'Vehicles', p_col: 'Pedestrians'})
        return df[['year', 'intersection', 'Vehicles', 'Pedestrians']]
    
    except Exception as e:
        st.error(f"Error processing file: {e}")
        return pd.DataFrame()

if uploaded_file:
    df = load_data(uploaded_file)
    
    if not df.empty:
        # Expandable Sidebar for mobile users
        st.sidebar.header("Comparison Settings")
        intersections = sorted(df['intersection'].unique())
        selected = st.sidebar.multiselect("Select Intersections", intersections, default=intersections[:1])
        
        y_min, y_max = int(df['year'].min()), int(df['year'].max())
        years = st.sidebar.slider("Select Year Range", y_min, y_max, (y_min, y_max))
        
        filtered = df[(df['intersection'].isin(selected)) & (df['year'].between(*years))]
        
        if not filtered.empty:
            # Aggregate by year
            grouped = filtered.groupby(['year', 'intersection']).sum(numeric_only=True).reset_index()
            
            tab1, tab2 = st.tabs(["🚗 Vehicle Traffic", "🚶 Pedestrian Traffic"])
            with tab1:
                st.plotly_chart(px.line(grouped, x='year', y='Vehicles', color='intersection', markers=True))
            with tab2:
                st.plotly_chart(px.bar(grouped, x='year', y='Pedestrians', color='intersection', barmode='group'))
        else:
            st.warning("Please select at least one intersection from the sidebar menu.")
        
