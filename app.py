import streamlit as st
import pandas as pd
import plotly.express as px
import io

st.set_page_config(page_title="Toronto Traffic Fixed", layout="wide")
st.title("🚦 Toronto Traffic Intersection Comparison")

uploaded_file = st.file_uploader("Upload 'tmc_summary_data.csv' here", type="csv")

@st.cache_data
def load_data(file_bytes):
    try:
        # Load with high-compatibility settings
        # encoding_errors='ignore' stops the 'None' error caused by weird symbols
        df = pd.read_csv(
            io.BytesIO(file_bytes), 
            on_bad_lines='skip', 
            engine='python', 
            encoding_errors='ignore',
            skip_blank_lines=True
        )
        
        # Standardize headers to find data even if the City changes names
        df.columns = [str(c).strip().lower() for c in df.columns]
        
        # 1. Flexible Column Finder
        date_col = next((c for c in df.columns if 'date' in c), None)
        v_col = next((c for c in df.columns if 'v_tot' in c or 'veh' in c), None)
        p_col = next((c for c in df.columns if 'p_tot' in c or 'ped' in c), None)
        main_col = next((c for c in df.columns if 'main' in c or 'location' in c), None)
        cross_col = next((c for c in df.columns if 'cross' in c or 'x_st' in c), None)

        if not all([date_col, main_col, v_col]):
            st.error(f"Required columns missing. Headers found: {list(df.columns)}")
            return pd.DataFrame()

        # 2. Aggressive Cleaning
        df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
        df = df.dropna(subset=[date_col])
        df['year'] = df[date_col].dt.year.astype(int)
        
        # Create a clean label for the intersection
        df['intersection'] = df[main_col].astype(str) + " & " + df[cross_col].fillna('N/A').astype(str)
        
        # Convert traffic volumes to numbers (replaces 'None' or text with 0)
        df['Vehicles'] = pd.to_numeric(df[v_key if 'v_key' in locals() else v_col], errors='coerce').fillna(0)
        df['Pedestrians'] = pd.to_numeric(df[p_key if 'p_key' in locals() else p_col], errors='coerce').fillna(0)
        
        return df[['year', 'intersection', 'Vehicles', 'Pedestrians']]
    
    except Exception as e:
        st.error(f"Debug Info: {str(e)}")
        return pd.DataFrame()

if uploaded_file:
    # Use .getvalue() to handle the file safely in memory
    df = load_data(uploaded_file.getvalue())
    
    if not df.empty:
        st.sidebar.header("Select Intersections")
        all_ints = sorted(df['intersection'].unique())
        selected = st.sidebar.multiselect("Pick one or more:", all_ints, default=all_ints[:1])
        
        years = st.sidebar.slider("Year Range", int(df['year'].min()), int(df['year'].max()), (2010, 2026))
        
        filtered = df[(df['intersection'].isin(selected)) & (df['year'].between(*years))]
        
        if not filtered.empty:
            grouped = filtered.groupby(['year', 'intersection']).sum(numeric_only=True).reset_index()
            
            tab1, tab2 = st.tabs(["🚗 Vehicles", "🚶 Pedestrians"])
            with tab1:
                st.plotly_chart(px.line(grouped, x='year', y='Vehicles', color='intersection', markers=True))
            with tab2:
                st.plotly_chart(px.bar(grouped, x='year', y='Pedestrians', color='intersection', barmode='group'))
        else:
            st.warning("Please pick an intersection from the menu on the left.")
        
