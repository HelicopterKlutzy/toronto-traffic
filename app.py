import streamlit as st
import pandas as pd
import plotly.express as px

# 1. Setup Page
st.set_page_config(page_title="Toronto Traffic Dashboard", layout="wide")
st.title("🚦 Toronto Traffic Intersection Comparison")
st.markdown("Compare **Vehicle** and **Pedestrian** volumes across different years.")

# 2. Resilient Data Loading
@st.cache_data
def load_data(uploaded_file=None):
    # Direct Datastore URL (Most stable for Toronto Open Data)
    csv_url = "https://ckan0.cf.opendata.inter.prod-toronto.ca"
    
    try:
        if uploaded_file is not None:
            df = pd.read_csv(uploaded_file, on_bad_lines='skip', engine='python')
        else:
            df = pd.read_csv(csv_url, on_bad_lines='skip', engine='python')
        
        # --- SMART COLUMN DETECTION ---
        # Convert all headers to lowercase for searching
        cols = {c.lower().strip(): c for c in df.columns}
        
        date_key = next((v for k, v in cols.items() if 'date' in k), None)
        v_key = next((v for k, v in cols.items() if 'v_tot' in k or 'veh' in k), None)
        p_key = next((v for k, v in cols.items() if 'p_tot' in k or 'ped' in k), None)
        main_key = next((v for k, v in cols.items() if 'main' in k), 'main')
        cross_key = next((v for k, v in cols.items() if 'cross' in k), 'cross_st')

        if not date_key:
            return None, f"Could not find Date column. Found: {list(df.columns)}"

        # --- DATA CLEANING ---
        df[date_key] = pd.to_datetime(df[date_key], errors='coerce')
        df = df.dropna(subset=[date_key])
        df['year'] = df[date_key].dt.year.astype(int)
        
        # Create intersection labels
        df['intersection'] = df[main_key].astype(str) + " & " + df[cross_key].astype(str)
        
        # Standardize for plotting
        df = df.rename(columns={v_key: 'Vehicles', p_key: 'Pedestrians'})
        return df[['year', 'intersection', 'Vehicles', 'Pedestrians']], None

    except Exception as e:
        return None, str(e)

# 3. Sidebar UI
st.sidebar.header("Data Source")
user_file = st.sidebar.file_uploader("Optional: Upload tmc_summary_data.csv", type="csv")

# Load Data
df, error_msg = load_data(user_file)

if df is not None:
    st.sidebar.divider()
    st.sidebar.header("Filters")
    
    # Intersection Multi-select
    intersections = sorted(df['intersection'].unique())
    selected = st.sidebar.multiselect("Select Intersections", intersections, default=intersections[:2])

    # Year Slider
    min_y, max_y = int(df['year'].min()), int(df['year'].max())
    year_range = st.sidebar.slider("Select Year Range", min_y, max_y, (min_y, max_y))

    # Apply Filters
    filtered = df[(df['intersection'].isin(selected)) & (df['year'].between(*year_range))]

    if not filtered.empty:
        # Group data by year and intersection
        grouped = filtered.groupby(['year', 'intersection']).sum(numeric_only=True).reset_index()

        tab1, tab2 = st.tabs(["🚗 Vehicle Trends", "🚶 Pedestrian Trends"])

        with tab1:
            fig_v = px.line(grouped, x='year', y='Vehicles', color='intersection', markers=True,
                           title="Annual Vehicle Volume")
            st.plotly_chart(fig_v, use_container_width=True)

        with tab2:
            fig_p = px.bar(grouped, x='year', y='Pedestrians', color='intersection', barmode='group',
                          title="Annual Pedestrian Volume")
            st.plotly_chart(fig_p, use_container_width=True)
            
        with st.expander("View Filtered Data Table"):
            st.dataframe(filtered)
    else:
        st.info("Choose intersections and years from the sidebar to see the charts.")

else:
    st.error(f"Failed to load data: {error_msg}")
    st.info("Tip: If the automated link is broken, download the 'TMC Summary Data' CSV from the Toronto Open Data portal and upload it here.")
        
