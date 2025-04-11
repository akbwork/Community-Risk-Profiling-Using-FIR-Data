import streamlit as st
import pandas as pd
import geopandas as gpd
import plotly.express as px
import plotly.graph_objects as go
import folium
from folium.features import GeoJsonTooltip
from streamlit_folium import folium_static

# Page configuration
st.set_page_config(layout="wide", page_title="Crime Analysis Dashboard", page_icon="🚨")

# Title and introduction
st.title("🚨 Geospatial Crime Mapping Dashboard")
st.markdown("""
This dashboard visualizes crime data across Indian districts, helping to identify high-risk areas and crime trends.
""")

# Load Data
@st.cache_data
def load_data():
    df_2001_2012 = pd.read_csv("/Users/ananthakrishnab/Desktop/Projects/Community Risk Profiling Using FIR Data/dataset/State-wise data from 2001 is classified according to 40+factors/crime/crime/01_District_wise_crimes_committed_IPC_2001_2012.csv")
    df_2013 = pd.read_csv("/Users/ananthakrishnab/Desktop/Projects/Community Risk Profiling Using FIR Data/dataset/State-wise data from 2001 is classified according to 40+factors/crime/crime/01_District_wise_crimes_committed_IPC_2013.csv")
    district_geo = gpd.read_file("/Users/ananthakrishnab/Downloads/india_district.geojson")
    return df_2001_2012, df_2013, district_geo

# Load and prepare data
with st.spinner("Loading data..."):
    df_2001_2012, df_2013, district_geo = load_data()
    
    # Combine Data
    df_all_years = pd.concat([df_2001_2012, df_2013], ignore_index=True)
    df_all_years.columns = df_all_years.columns.str.strip()
    
    # Aggregate Data
    crime_totals = df_all_years.groupby(['STATE/UT', 'DISTRICT'])['TOTAL IPC CRIMES'].sum().reset_index()
    crime_totals.rename(columns={'TOTAL IPC CRIMES': 'Total_Crimes'}, inplace=True)
    
    # Merge with GeoJSON
    district_geo['DISTRICT'] = district_geo['NAME_2'].str.upper().str.strip()
    crime_totals['DISTRICT'] = crime_totals['DISTRICT'].str.upper().str.strip()
    district_map = district_geo.merge(crime_totals, on='DISTRICT', how='left')

    # Prepare crime categories
    df_all_years['HEINOUS_TOTAL'] = df_all_years[['MURDER', 'RAPE', 'DACOITY', 'KIDNAPPING & ABDUCTION', 'ROBBERY']].sum(axis=1)
    df_all_years['PETTY_TOTAL'] = df_all_years[['THEFT', 'BURGLARY', 'CHEATING', 'COUNTERFIETING']].sum(axis=1)

# Sidebar
st.sidebar.header("Dashboard Controls")

# Sidebar Filters
state_filter = st.sidebar.selectbox("Select State/UT", options=["All"] + sorted(df_all_years['STATE/UT'].unique().tolist()))
year_filter = st.sidebar.slider("Select Year Range", 
                               min_value=int(df_all_years['YEAR'].min()),
                               max_value=int(df_all_years['YEAR'].max()),
                               value=(int(df_all_years['YEAR'].min()), int(df_all_years['YEAR'].max())))

# Filter Data
filtered_data = df_all_years.copy()
if state_filter != "All":
    filtered_data = filtered_data[filtered_data['STATE/UT'] == state_filter]
    district_map_filtered = district_map[district_map['NAME_1'].str.upper() == state_filter.upper()]
else:
    district_map_filtered = district_map

filtered_data = filtered_data[(filtered_data['YEAR'] >= year_filter[0]) & (filtered_data['YEAR'] <= year_filter[1])]

# Main content area - organized in tabs
tab1, tab2, tab3 = st.tabs(["📊 Crime Overview", "🗺️ Geospatial Analysis", "📈 Detailed Analytics"])

with tab1:
    # Overview metrics
    st.subheader("Crime Statistics Overview")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total IPC Crimes", f"{filtered_data['TOTAL IPC CRIMES'].sum():,}")
    with col2:
        st.metric("Heinous Crimes", f"{filtered_data['HEINOUS_TOTAL'].sum():,}")
    with col3:
        st.metric("Petty Crimes", f"{filtered_data['PETTY_TOTAL'].sum():,}")
    with col4:
        st.metric("Districts Analyzed", f"{filtered_data['DISTRICT'].nunique():,}")
    
    # Crime breakdown pie chart
    st.subheader("Crime Type Breakdown")
    crime_cols = ['MURDER', 'RAPE', 'KIDNAPPING & ABDUCTION', 'DACOITY', 'ROBBERY', 'BURGLARY', 'THEFT', 'CHEATING', 'COUNTERFIETING']
    crime_totals = filtered_data[crime_cols].sum().reset_index()
    crime_totals.columns = ['Crime Type', 'Count']
    
    col1, col2 = st.columns(2)
    with col1:
        fig_pie = px.pie(
            crime_totals,
            values='Count',
            names='Crime Type',
            title='Distribution of Crime Types',
            hole=0.3,
            color_discrete_sequence=px.colors.qualitative.Bold
        )
        st.plotly_chart(fig_pie)
    
    with col2:
        # Heinous vs Petty crimes
        heinous_vs_petty = pd.DataFrame({
            'Category': ['Heinous Crimes', 'Petty Crimes'],
            'Count': [filtered_data['HEINOUS_TOTAL'].sum(), filtered_data['PETTY_TOTAL'].sum()]
        })
        
        fig_bar = px.bar(
            heinous_vs_petty,
            x='Category',
            y='Count',
            title='Heinous vs Petty Crimes',
            color='Category',
            color_discrete_sequence=['#ff6b6b', '#48dbfb']
        )
        st.plotly_chart(fig_bar)

with tab2:
    st.subheader("Geospatial Crime Distribution")
    
    # Plot Choropleth with Plotly
    col1, col2 = st.columns([3, 1])
    
    with col1:
        fig = px.choropleth(
            district_map_filtered,
            geojson=district_map_filtered.geometry.__geo_interface__,
            locations=district_map_filtered.index,
            color='Total_Crimes',
            hover_name='DISTRICT',
            projection='mercator',
            color_continuous_scale='Reds',
            title='Total IPC Crimes by District'
        )
        fig.update_geos(fitbounds="locations", visible=False)
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.write("### Top 5 Districts")
        # Ensure 'Total_Crimes' column exists before using it
        if 'Total_Crimes' not in crime_totals.columns:
            st.error("The column 'Total_Crimes' is missing in the dataset. Please check the data processing steps.")
        else:
            # Proceed with finding the top districts
            top_districts = crime_totals.nlargest(5, 'Total_Crimes')
            for i, row in top_districts.iterrows():
                st.markdown(f"**{row['DISTRICT']}** ({row['STATE/UT']}): {row['Total_Crimes']:,} crimes")
    
    # Folium Map
    st.subheader("Interactive Map")
    m = folium.Map(location=[22.5, 80], zoom_start=5, tiles="cartodbpositron")
    
    # Add tooltip
    tooltip = GeoJsonTooltip(
        fields=['DISTRICT', 'Total_Crimes'],
        aliases=['District:', 'Total Crimes:'],
        localize=True,
        sticky=False,
        labels=True
    )
    
    # Add choropleth
    folium.Choropleth(
        geo_data=district_map_filtered.__geo_interface__,
        name='choropleth',
        data=district_map_filtered,
        columns=['DISTRICT', 'Total_Crimes'],
        key_on='feature.properties.DISTRICT',
        fill_color='YlOrRd',
        fill_opacity=0.7,
        line_opacity=0.2,
        legend_name='Total IPC Crimes'
    ).add_to(m)
    
    folium_static(m, width=1000, height=600)

with tab3:
    st.subheader("Crime Trends and Analytics")
    
    # Yearly Trend Analysis
    yearly_trend = filtered_data.groupby('YEAR')[['TOTAL IPC CRIMES', 'HEINOUS_TOTAL', 'PETTY_TOTAL']].sum().reset_index()
    
    fig_yearly = px.line(
        yearly_trend,
        x='YEAR',
        y=['TOTAL IPC CRIMES', 'HEINOUS_TOTAL', 'PETTY_TOTAL'],
        labels={'value': 'Number of Crimes', 'variable': 'Crime Category'},
        title='Yearly Crime Trends',
        markers=True
    )
    st.plotly_chart(fig_yearly, use_container_width=True)
    
    # State-wise comparison
    col1, col2 = st.columns(2)
    
    with col1:
        state_crimes = df_all_years.groupby('STATE/UT')['TOTAL IPC CRIMES'].sum().nlargest(10).reset_index()
        fig_states = px.bar(
            state_crimes,
            x='STATE/UT',
            y='TOTAL IPC CRIMES',
            title='Top 10 States by Crime Volume',
            color='TOTAL IPC CRIMES',
            color_continuous_scale='Viridis'
        )
        fig_states.update_layout(xaxis_tickangle=-45)
        st.plotly_chart(fig_states, use_container_width=True)
    
    with col2:
        # Crime growth rate
        if len(yearly_trend) > 1:
            yearly_trend['Growth_Rate'] = yearly_trend['TOTAL IPC CRIMES'].pct_change() * 100
            fig_growth = px.bar(
                yearly_trend.dropna(),
                x='YEAR',
                y='Growth_Rate',
                title='Year-over-Year Crime Growth Rate (%)',
                color='Growth_Rate',
                color_continuous_scale='RdBu_r',
                text_auto='.1f'
            )
            fig_growth.update_traces(texttemplate='%{text}%', textposition='outside')
            st.plotly_chart(fig_growth, use_container_width=True)
        else:
            st.info("Insufficient data to calculate growth rates.")

# Footer
st.markdown("---")
st.markdown("**Crime Analysis Dashboard** • Data Source: National Crime Records Bureau")