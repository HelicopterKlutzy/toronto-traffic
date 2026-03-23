import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Toronto Traffic Fix", layout="wide")
st.title("🚦 Toronto Traffic Intersection Comparison")

uploaded_file = st.file_uploader("Upload 'tmc_summary_data.csv' here", type="csv")

@st.cache_data
def load_data(file):
    try:
        # 1. Load file with flexible settings
        df = pd.read_csv(file, on_bad_lines='skip', engine='python', skip_blank_lines=True)
        
        # 2. Clean headers (Lowercase and strip spaces)
        df.columns = [str(c).strip().lower() for c in df.columns]
        
        # 3. Smart Column Mapping (Finds 'date', 'v_tot', 'p_tot', 'main')
        date_col = next((c for c in df.columns if 'date' in c), None)
        v_col = next((c for c in df.columns if 'v_tot' in c or 'veh' in c), None)
        p_col = next((c for c in df.columns if 'p_tot' in c or 'ped' in c), None)
        main_col = next((c for c in df.columns if 'main' in c or 'location' in c), None)
        cross_col = next((c for c in df.columns if 'cross' in c or 'x_st' in c), None)

        # Fail-safe check
        if not all([date_col, main_col, v_col]):
            st.error(f"Missing required columns! Found these: {list(df.columns)}")
            return pd.DataFrame()

        # 4. Data Cleaning
        df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
        df = df.dropna(subset=[date_col])
        df['year'] = df[date_col].dt.year.astype(int)
        
        # Merge street names into one 'Intersection' label
        df['intersection'] = df[main_col].astype(str) + " & " + df[cross_col].fillna('Unknown').astype(str)
        
        # Standardize volume names for internal use
        df = df.rename(columns={v_col: 'Vehicles', p_col: 'Pedestrians'})
        
        # Final cleanup: Remove any rows where 'Vehicles' isn't a number
        df['Vehicles'] = pd.to_numeric(df['Vehicles'], errors='coerce').fillna(0)
        df['Pedestrians'] = pd.to_numeric(df['Pedestrians'], errors='coerce').fillna(0)
        
        return df[['year', 'intersection', 'Vehicles', 'Pedestrians']]
    
    except Exception as e:
        st.error(f"Critical Processing Error: {str(e)}")
        return pd.DataFrame()

if uploaded_file:
    df = load_data(uploaded_file)
    
    if not df.empty:
        # Sidebar Filters
        st.sidebar.header("Comparison Settings")
        
        # Intersection List
        all_intersections = sorted(df['intersection'].unique())
        selected = st.sidebar.multiselect("Select Intersections", all_intersections, default=all_intersections[:1])
        
        # Year Slider
        min_y, max_y = int(df['year'].min()), int(df['year'].max())
        years = st.sidebar.slider("Select Year Range", min_y, max_y, (min_y, max_y))
        
        # Filter the data
        filtered = df[(df['intersection'].isin(selected)) & (df['year'].between(*years))]
        
        if not filtered.empty:
            # Group by year to get annual totals
            grouped = filtered.groupby(['year', 'intersection']).sum(numeric_only=True).reset_index()
            
            tab1, tab2 = st.tabs(["🚗 Vehicle Traffic", "🚶 Pedestrian Traffic"])
            with tab1:
                st.plotly_chart(px.line(grouped, x='year', y='Vehicles', color='intersection', markers=True, 
                                        title="Annual Vehicle Volumes"))
            with tab2:
                st.plotly_chart(px.bar(grouped, x='year', y='Pedestrians', color='intersection', barmode='group',
                                       title="Annual Pedestrian Volumes"))
            
            with st.expander("View Raw Data Table"):
                st.dataframe(filtered)
        else:
            st.warning("Please select at least one intersection from the sidebar menu to see results.")
            
