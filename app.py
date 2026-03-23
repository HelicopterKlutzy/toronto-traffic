import streamlit as st
import pandas as pd
import plotly.express as px

# 1. Setup Page
st.set_page_config(page_title="Toronto Traffic: Pedestrians vs Vehicles", layout="wide")
st.title("🚦 Toronto Traffic: Pedestrians vs. Vehicles")

@st.cache_data
def load_data():
    # Use the 'tmc_summary_data.csv' from Toronto Open Data
    df = pd.read_csv('tmc_summary_data.csv')
    df['count_date'] = pd.to_datetime(df['count_date'])
    df['year'] = df['count_date'].dt.year
    return df

try:
    df = load_data()

    # 2. Sidebar Filters
    st.sidebar.header("Comparison Settings")
    
    # Mode Selection
    view_mode = st.sidebar.radio("Select View:", ["Total Traffic", "Pedestrians vs. Vehicles"])

    # Intersection Selection
    all_intersections = sorted(df['main'].unique())
    selected_intersections = st.sidebar.multiselect(
        "Select Intersections", 
        options=all_intersections,
        default=all_intersections[:1] # Start with one for clarity
    )

    # 3. Data Filtering & Reshaping
    filtered_df = df[df['main'].isin(selected_intersections)]
    
    if view_mode == "Total Traffic":
        # Standard trend chart
        chart_data = filtered_df.groupby(['year', 'main'])['v_tot'].sum().reset_index()
        fig = px.line(chart_data, x='year', y='v_tot', color='main', title="Total Annual Volume")
    
    else:
        # Reshape data for Pedestrian vs Vehicle comparison
        # v_tot = vehicle total, p_tot = pedestrian total
        comp_df = filtered_df.groupby(['year', 'main'])[['v_tot', 'p_tot']].sum().reset_index()
        
        # Melting the data makes it easier for Plotly to color-code by "Type"
        melted_df = comp_df.melt(
            id_vars=['year', 'main'], 
            value_vars=['v_tot', 'p_tot'],
            var_name='Traffic Type', 
            value_name='Volume'
        )
        # Rename for readability
        melted_df['Traffic Type'] = melted_df['Traffic Type'].map({'v_tot': 'Vehicles', 'p_tot': 'Pedestrians'})
        
        fig = px.bar(
            melted_df, 
            x='year', 
            y='Volume', 
            color='Traffic Type',
            barmode='group', # Side-by-side bars
            facet_col='main', # Separate chart for each intersection if multiple selected
            title="Pedestrians vs. Vehicles Comparison"
        )

    # 4. Display Chart
    st.plotly_chart(fig, use_container_width=True)

except Exception as e:
    st.error(f"Error loading or processing data: {e}")
    
