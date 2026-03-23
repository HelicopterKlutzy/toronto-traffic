import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Toronto Traffic Fix", layout="wide")
st.title("🚦 Toronto Traffic Intersection Comparison")

@st.cache_data
def load_traffic_data():
    csv_url = "https://ckan0.cf.opendata.inter.prod-toronto.ca"
    try:
        # Load with python engine to handle malformed lines
        df = pd.read_csv(csv_url, sep=',', on_bad_lines='skip', engine='python')
        
        # --- ROBUST COLUMN MAPPING ---
        cols = {c.lower(): c for c in df.columns}
        
        # 1. Find Date Column (Look for 'date')
        date_col = next((v for k, v in cols.items() if 'date' in k), None)
        # 2. Find Volume Columns (Look for 'v_tot' and 'p_tot')
        v_col = next((v for k, v in cols.items() if 'v_tot' in k), None)
        p_col = next((v for k, v in cols.items() if 'p_tot' in k), None)
        # 3. Find Intersection Columns
        main_col = next((v for k, v in cols.items() if 'main' in k), 'main')
        cross_col = next((v for k, v in cols.items() if 'cross' in k), 'cross_st')

        if not date_col:
            st.error(f"Could not find a date column. Available: {list(df.columns)}")
            return pd.DataFrame()

        # Clean Dates & Create Year
        df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
        df = df.dropna(subset=[date_col])
        df['year'] = df[date_col].dt.year.astype(int)
        
        # Create Intersection Label
        df['intersection'] = df[main_col].fillna('Unknown') + " & " + df[cross_col].fillna('Unknown')
        
        # Rename volumes for consistent internal use
        df = df.rename(columns={v_col: 'v_tot', p_col: 'p_tot'})
        
        return df[['year', 'intersection', 'v_tot', 'p_tot']]
    except Exception as e:
        st.error(f"Resilience Error: {e}")
        return pd.DataFrame()

df = load_traffic_data()

if not df.empty:
    st.sidebar.header("Filters")
    all_intersections = sorted(df['intersection'].unique())
    selected = st.sidebar.multiselect("Select Intersections", all_intersections, default=all_intersections[:2])

    year_range = st.sidebar.slider("Select Years", int(df['year'].min()), int(df['year'].max()), (2010, 2024))

    filtered = df[(df['intersection'].isin(selected)) & (df['year'].between(*year_range))]

    if not filtered.empty:
        grouped = filtered.groupby(['year', 'intersection'])[['v_tot', 'p_tot']].sum().reset_index()
        
        t1, t2 = st.tabs(["🚗 Vehicles", "🚶 Pedestrians"])
        with t1:
            st.plotly_chart(px.line(grouped, x='year', y='v_tot', color='intersection', markers=True))
        with t2:
            st.plotly_chart(px.bar(grouped, x='year', y='p_tot', color='intersection', barmode='group'))
    else:
        st.warning("No data for these selections.")
                                    
