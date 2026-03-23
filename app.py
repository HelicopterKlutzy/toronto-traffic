import streamlit as st
import pandas as pd
import plotly.express as px

# 1. Page Configuration
st.set_page_config(page_title="Toronto Traffic Comparison", layout="wide")
st.title("🚦 Toronto Traffic Intersection Comparison")

# 2. Resilient Data Loading
@st.cache_data
def load_traffic_data():
    # Direct CSV link for TMC Summary Data
    csv_url = "https://ckan0.cf.opendata.inter.prod-toronto.ca"
    
    try:
        # FIX: on_bad_lines='skip' ignores the malformed lines that caused your error
        # engine='python' is more robust for files with inconsistent formatting
        df = pd.read_csv(
            csv_url, 
            low_memory=False, 
            on_bad_lines='skip', 
            engine='python'
        )
        
        # Basic Cleaning
        df['count_date'] = pd.to_datetime(df['count_date'], errors='coerce')
        df = df.dropna(subset=['count_date'])
        df['year'] = df['count_date'].dt.year.astype(int)
        df['intersection'] = df['main'].fillna('') + " & " + df['cross_st'].fillna('')
        
        return df
    except Exception as e:
        st.error(f"Failed to process data: {e}")
        return pd.DataFrame()

# 3. App Logic
df = load_traffic_data()

if not df.empty:
    st.sidebar.header("Filters")
    
    # Selection UI
    all_intersections = sorted(df['intersection'].unique())
    selected_intersections = st.sidebar.multiselect(
        "Select Intersections", 
        options=all_intersections,
        default=all_intersections[:1]
    )

    min_year, max_year = int(df['year'].min()), int(df['year'].max())
    year_range = st.sidebar.slider("Select Year Range", min_year, max_year, (min_year, max_year))

    # Filtered Data
    filtered_df = df[
        (df['intersection'].isin(selected_intersections)) & 
        (df['year'] >= year_range[0]) & 
        (df['year'] <= year_range[1])
    ]

    if not filtered_df.empty:
        # Aggregate totals (v_tot = vehicles, p_tot = pedestrians)
        grouped = filtered_df.groupby(['year', 'intersection'])[['v_tot', 'p_tot']].sum().reset_index()

        tab1, tab2 = st.tabs(["🚗 Vehicles", "🚶 Pedestrians vs Vehicles"])

        with tab1:
            fig1 = px.line(grouped, x='year', y='v_tot', color='intersection', markers=True,
                          title="Annual Vehicle Traffic Trends")
            st.plotly_chart(fig1, use_container_width=True)

        with tab2:
            melted = grouped.melt(id_vars=['year', 'intersection'], 
                                  value_vars=['v_tot', 'p_tot'],
                                  var_name='Type', value_name='Volume')
            melted['Type'] = melted['Type'].replace({'v_tot': 'Vehicles', 'p_tot': 'Pedestrians'})
            
            fig2 = px.bar(melted, x='year', y='Volume', color='Type', barmode='group',
                         facet_col='intersection', title="Volume Breakdown")
            st.plotly_chart(fig2, use_container_width=True)
    else:
        st.info("No data found for the selected filters.")
else:
    st.error("Could not load data. The source file may be temporarily unavailable.")
    
