import streamlit as st
import pandas as pd
import plotly.express as px
import os

# --- Configuration ---
# Hard-code your file path here. 
# If it's in the same folder as app.py, just use the file name.
FILE_PATH = "OCO3_SAM_GT200_ratios.txt" 
# ---------------------

st.set_page_config(page_title="OCO-3 SAM Success Rate Map", layout="wide")
st.title("OCO-3 SAM Success Rate Map Viewer")

# Check if the hard-coded file actually exists
if not os.path.exists(FILE_PATH):
    st.error(f"File not found: `{FILE_PATH}`. Please ensure the file is in the correct location.")
else:
    try:
        # Read the file. Adjust 'sep' if your file uses tabs ('\t') or semicolons (';')
        df = pd.read_csv(FILE_PATH, sep=',', engine='python')
        
        with st.expander("Preview Data"):
            st.dataframe(df.head())
            
        # Define the required columns
        required_columns = ['Target Name', 'latitude', 'longitude', 'count_GT200_soundings', 'count_all', 'ratio']
        
        # Check for missing columns
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        if missing_columns:
            st.error(f"The file is missing the following required columns: {', '.join(missing_columns)}")
        else:
            # Ensure proper data types
            df['latitude'] = pd.to_numeric(df['latitude'], errors='coerce')
            df['longitude'] = pd.to_numeric(df['longitude'], errors='coerce')
            df['ratio'] = pd.to_numeric(df['ratio'], errors='coerce')
            
            # Drop rows with invalid coordinates or ratio
            df = df.dropna(subset=['latitude', 'longitude', 'ratio'])
            
            st.subheader("Interactive Map")

            # Generate Map
            fig = px.scatter_mapbox(
                df,
                lat="latitude",
                lon="longitude",
                color="ratio",
                hover_name="Target Name",
                hover_data={
                    "latitude": ':.2f', 
                    "longitude": ':.2f',
                    "count_GT200_soundings": ':.0f',
                    "count_all": ':.0f',
                    "ratio": ':.2f'
                },
                color_continuous_scale=px.colors.sequential.Viridis,
                range_color=[0, 1], # Locks the color scale from 0 to 1
                zoom=0,
                center={"lat": 0, "lon": 0},
                mapbox_style='carto-positron',
                title="SAM Locations Colored by Success Rate"
            )
            
            fig.update_layout(margin={"r":0,"t":40,"l":0,"b":0})
            #st.plotly_chart(fig, use_container_width=True)
            st.plotly_chart(fig, use_container_width=True, config={"scrollZoom": True})

    except pd.errors.ParserError:
        st.error("Error parsing the file. Please check if it's correctly formatted (e.g., comma-separated).")
    except Exception as e:
        st.error(f"An unexpected error occurred: {e}")
