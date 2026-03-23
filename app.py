import streamlit as st
import pandas as pd
import plotly.express as px

# 1. Page Configuration
st.set_page_config(page_title="Toronto Traffic Comparison", layout="wide")
st.title("🚦 Toronto Traffic Intersection Comparison")
st.markdown("Comparing **Vehicle** and **Pedestrian** volumes using Toronto Open Data.")

# 2. Robust Data Loading
@st.cache_data
def load_traffic_data():
    # Direct CSV download link from Toronto Open Data (TMC Summary Data)
    # This avoids the "Line 1 Column 1" JSON error
    csv_url = "https://ckan0.cf.opendata.inter.prod-toronto.ca"
    
    try:
        # load_memory=False handles large datasets with mixed data types better
        df = pd.read_csv(csv_url, low_memory=False)
        
        # Data Cleaning
        df['count_date'] = pd.to_datetime(df['count_date'], errors='coerce')
        df = df.dropna(subset=['count_date']) # Remove rows with invalid dates
        df['year'] = df['count_date'].dt.year.astype(int)
        
        # Identify intersection name (using 'main' street and 'cross' street)
        df['intersection'] = df['main'] + " & " + df['cross_st']
        
        return df
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return pd.DataFrame()

# 3. App Logic
df = load_traffic_data()

if not df.empty:
    # Sidebar: Intersections
    st.sidebar.header("Filters")
    all_intersections = sorted(df['intersection'].unique())
    selected_intersections = st.sidebar.multiselect(
        "Select Intersections", 
        options=all_intersections,
        default=all_intersections[:2]
    )

    # Sidebar: Years
    min_year, max_year = int(df['year'].min()), int(df['year'].max())
    year_range = st.sidebar.slider("Select Year Range", min_year, max_year, (min_year, max_year))

    # Filter Data
    mask = (df['intersection'].isin(selected_intersections)) & \
           (df['year'] >= year_range[0]) & (df['year'] <= year_range[1])
    filtered_df = df[mask]

    if not filtered_df.empty:
        # Group data for plotting
        # v_tot = vehicles, p_tot = pedestrians
        grouped = filtered_df.groupby(['year', 'intersection'])[['v_tot', 'p_tot']].sum().reset_index()

        # Tabs for different views
        tab1, tab2 = st.tabs(["🚗 Total Traffic", "🚶 Pedestrians vs Vehicles"])

        with tab1:
            fig1 = px.line(grouped, x='year', y='v_tot', color='intersection', markers=True,
                          labels={'v_tot': 'Vehicle Volume', 'year': 'Year'},
                          title="Annual Vehicle Trends")
            st.plotly_chart(fig1, use_container_width=True)

        with tab2:
            # Melt data for comparison bars
            melted = grouped.melt(id_vars=['year', 'intersection'], 
                                  value_vars=['v_tot', 'p_tot'],
                                  var_name='Type', value_name='Volume')
            melted['Type'] = melted['Type'].map({'v_tot': 'Vehicles', 'p_tot': 'Pedestrians'})
            
            fig2 = px.bar(melted, x='year', y='Volume', color='Type', barmode='group',
                         facet_col='intersection', facet_col_wrap=2,
                         title="Pedestrian vs. Vehicle Breakdown")
            st.plotly_chart(fig2, use_container_width=True)
            
        with st.expander("View Raw Data"):
            st.dataframe(filtered_df)
    else:
        st.info("Select intersections and years from the sidebar to begin.")
else:
    st.error("Failed to load data from Toronto Open Data. Please check your connection.")
    
