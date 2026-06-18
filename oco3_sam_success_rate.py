import streamlit as st
import pandas as pd
import plotly.express as px
import os

# --- Configuration ---
#FILE_PATH = "OCO3_SAM_GT200_ratios.txt" 
FILE_PATH = "sam_co2_stats_Fisher_20260617.csv" 
#SIF_FILE_PATH = "OCO3_SAM_GT200_SIF_ratios.txt" 
SIF_FILE_PATH = "sam_sif_stats2_Fisher_20260617.csv" 
# ---------------------


def process_co2_data(df):
    """Processes the CO2 dataset."""
    df.columns = df.columns.str.strip()
    
    # Replace -999 fill values
    df['Median Latitude'] = df['Median Latitude'].replace(-999, pd.NA)
    df['Median Longitde'] = df['Median Longitude'].replace(-999, pd.NA)
    
    # Calculate row-level success rate
    df['row_success_rate'] = df['N Good Quality Soundings'] / df['N L2 Soundings'].replace(0, pd.NA)
    
    # Group by Target ID
    df_grouped = df.groupby('Target ID').agg({
        'Target Name': 'first',                
        'Median Latitude': 'mean',             
        'Median Longitude': 'mean',                 
        'N Good Quality Soundings': 'sum',     
        'N L2 Soundings': 'sum',               
        'row_success_rate': 'mean'             
    }).reset_index()
    
    # Rename columns for Mapbox
    return df_grouped.rename(columns={
        'Median Latitude': 'latitude',
        'Median Longitude': 'longitude',
        'N Good Quality Soundings': 'count_GT200_soundings',
        'N L2 Soundings': 'count_all',
        'row_success_rate': 'SAM_success_rate'
    })


def process_sif_data(df):
    """Processes the SIF dataset."""
    df.columns = df.columns.str.strip()
    
    # Replace -999 fill values
    df['Site Latitude'] = df['Site Latitude'].replace(-999, pd.NA)
    df['Site Longitude'] = df['Site Longitude'].replace(-999, pd.NA)
    
    # Calculate row-level success rate (using N Good Soundings / Total Soundings)
    df['row_success_rate'] = df['N Good Soundings'] / df['Total Soundings'].replace(0, pd.NA)
    
    # Group by Target ID
    df_grouped = df.groupby('Target ID').agg({
        'Target Name': 'first',
        'Site Latitude': 'mean',
        'Site Longitude': 'mean',
        'N Good Soundings': 'sum',
        'Total Soundings': 'sum',
        'row_success_rate': 'mean'
    }).reset_index()
    
    # Rename columns for Mapbox
    return df_grouped.rename(columns={
        'Site Latitude': 'latitude',
        'Site Longitude': 'longitude',
        'N Good Soundings': 'count_GT200_soundings',
        'Total Soundings': 'count_all',
        'row_success_rate': 'SAM_success_rate'
    })


st.set_page_config(page_title="OCO-3 SAM Success Rate Map", layout="wide")
st.title("OCO-3 SAM Success Rate Map Viewer")

# Check if both hard-coded files actually exist
if not os.path.exists(FILE_PATH) or not os.path.exists(SIF_FILE_PATH):
    st.error(f"Missing files. Please ensure both `{FILE_PATH}` and `{SIF_FILE_PATH}` are in the correct location.")
else:
    try:
        # Read the files
        raw_df_co2 = pd.read_csv(FILE_PATH, sep=',', engine='python')
        raw_df_sif = pd.read_csv(SIF_FILE_PATH, sep=',', engine='python')
      
        # Process the raw files using their specific functions
        df_co2 = process_co2_data(raw_df_co2)
        df_sif = process_sif_data(raw_df_sif)
  
        # --- UI Toggle ---
        # Let the user choose which dataset to view
        dataset_choice = st.radio(
            "Select Variable to Display:", 
            options=["CO2", "SIF"], 
            horizontal=True
        )
        
        # Set variables based on the user's choice
        if dataset_choice == "CO2":
            active_df = df_co2
            active_colorscale = px.colors.sequential.Viridis
            active_title = "SAM Locations Colored by Success Rate (N converged CO2 retrievals > 200)"
        else:
            active_df = df_sif
            active_colorscale = px.colors.sequential.Viridis
            #active_colorscale = px.colors.sequential.YlGn
            active_title = "SAM Locations Colored by Success Rate (N 'Best Quality' SIF retrievals > 200)"

        # Display the data for the currently selected dataset
        with st.expander(f"Preview {dataset_choice} Data"):
            st.dataframe(active_df)
            
        # Define the required columns
        required_columns = ['Target Name', 'latitude', 'longitude', 'count_GT200_soundings', 'count_all', 'SAM_success_rate']
        
        # Check for missing columns in the active dataframe
        missing_columns = [col for col in required_columns if col not in active_df.columns]
        
        if missing_columns:
            st.error(f"The {dataset_choice} file is missing the following required columns: {', '.join(missing_columns)}")
        else:
            # Ensure proper data types
            active_df['latitude'] = pd.to_numeric(active_df['latitude'], errors='coerce')
            active_df['longitude'] = pd.to_numeric(active_df['longitude'], errors='coerce')
            active_df['SAM_success_rate'] = pd.to_numeric(active_df['SAM_success_rate'], errors='coerce')
            
            # Drop rows with invalid coordinates or ratio
            active_df = active_df.dropna(subset=['latitude', 'longitude', 'SAM_success_rate'])
            
            st.subheader("Interactive Map")

            # Generate Map using the active dataset and styling
            fig = px.scatter_mapbox(
                active_df,
                lat="latitude",
                lon="longitude",
                color="SAM_success_rate",
                hover_name="Target Name",
                hover_data={
                    "latitude": ':.2f', 
                    "longitude": ':.2f',
                    "count_GT200_soundings": ':.0f',
                    "count_all": ':.0f',
                    "SAM_success_rate": ':.2f'
                },
                color_continuous_scale=active_colorscale, # <--- Uses Viridis or Greens
                range_color=[0, 1],
                zoom=1,
                center={"lat": 0, "lon": 0},
                mapbox_style='carto-positron',
                title=active_title                        # <--- Uses CO2 or SIF title
            )
            
            # Adjust layout
            fig.update_layout(
              margin={"r":0,"t":40,"l":0,"b":0},
              height=800  
            )

            fig.update_traces(marker={"size": 12})

            # Render plot
            st.plotly_chart(fig, use_container_width=True, config={"scrollZoom": True})

    except pd.errors.ParserError:
        st.error("Error parsing one of the files. Please check if they are correctly formatted (e.g., comma-separated).")
    except Exception as e:
        st.error(f"An unexpected error occurred: {e}")


