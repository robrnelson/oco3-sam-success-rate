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
    # Clean up column names just in case there are trailing spaces
    df.columns = df.columns.str.strip()
    
    # Replace -999 fill values
    df['Median Latitude'] = df['Median Latitude'].replace(-999.0, pd.NA)
    df['Median Longitude'] = df['Median Longitude'].replace(-999.0, pd.NA) # <--- Corrected
    #df['Median Latitude'] = df['Median Latitude'].replace(-999, pd.NA)
    #df['Median Longitude'] = df['Median Longitude'].replace(-999, pd.NA) # <--- Corrected
    
    # Calculate row-level success rate
    df['row_success_rate'] = df['N Good Quality Soundings'] / df['N L2 Soundings'].replace(0, pd.NA)
    
    # Group by Target ID
    df_grouped = df.groupby('Target ID').agg({
        'Target Name': 'first',                
        'Median Latitude': 'mean',             
        'Median Longitude': 'mean',            # <--- Corrected
        'N Good Quality Soundings': 'sum',     
        'N L2 Soundings': 'sum',               
        'row_success_rate': 'mean',
        'Start Time': 'count'                  
    }).reset_index()
    
    # Rename columns for Mapbox
    return df_grouped.rename(columns={
        'Median Latitude': 'latitude',
        'Median Longitude': 'longitude',       # <--- Corrected
        'N Good Quality Soundings': 'count_GT200_soundings',
        'N L2 Soundings': 'count_all',
        'row_success_rate': 'SAM_good_quality_fraction',
        'Start Time': 'N_SAMs'                 
    })


def process_sif_data(df):
    df.columns = df.columns.str.strip()
    #df['Site Latitude'] = df['Site Latitude'].replace(-999, pd.NA)
    #df['Site Longitude'] = df['Site Longitude'].replace(-999, pd.NA)
    df['row_success_rate'] = df['N Good Soundings'] / df['Total Soundings'].replace(0, pd.NA)
    
    df_grouped = df.groupby('Target ID').agg({
        'Target Name': 'first',
        'Site Latitude': 'mean',
        'Site Longitude': 'mean',
        'N Good Soundings': 'sum',
        'Total Soundings': 'sum',
        'row_success_rate': 'mean',
        'Start Time': 'count'                  # <--- Add this to count the rows
    }).reset_index()
    
    return df_grouped.rename(columns={
        'Site Latitude': 'latitude',
        'Site Longitude': 'longitude',
        'N Good Soundings': 'count_GT200_soundings',
        'Total Soundings': 'count_all',
        'row_success_rate': 'SAM_good_quality_fraction',
        'Start Time': 'N_SAMs'                 # <--- Rename it to N_SAMs
    })


st.set_page_config(page_title="OCO-3 SAM Success Rate Map", layout="wide")
#st.title("OCO-3 SAM Success Rate Map Viewer")
st.title("OCO-3 SAM Good Retrieval Fraction Map Viewer")

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
            active_title = "SAM Locations Colored by the Mean Fraction of Good Quality Retrievals"
        else:
            active_df = df_sif
            active_colorscale = px.colors.sequential.Viridis
            active_title = "SAM Locations Colored by the Mean Fraction of Good Quality Retrievals"

        st.divider() # Adds a clean visual line to separate toggles from filters

        # --- Filtering UI ---
        st.write("### Data Filters")
        
        # 1. N_SAMs Slider
        min_possible = int(active_df['N_SAMs'].min())
        max_possible = int(active_df['N_SAMs'].max())
        
        selected_min_sams = st.slider(
            "Minimum N_SAMs:",
            min_value=min_possible,
            max_value=max_possible,
            value=min_possible,
            step=1
        )
        
        # 2. Target ID Prefix Checkboxes
        st.write("**Include Target IDs starting with:**")
        target_prefixes = ["C40", "cal", "coccon", "desert", "ecostress", "fossil", "sif", "tccon", "texmex", "val", "volcano"]
        
        # The Deselect All checkbox
        deselect_all = st.checkbox("Deselect All", value=False)
        
        cols = st.columns(4)
        selected_prefixes = []
        
        for i, prefix in enumerate(target_prefixes):
            with cols[i % 4]:
                # By tying the key to the deselect_all state, Streamlit will completely reset 
                # the checkboxes whenever you toggle "Deselect All", avoiding state conflicts!
                if st.checkbox(prefix, value=not deselect_all, key=f"{prefix}_{deselect_all}"):
                    selected_prefixes.append(prefix)

        st.write("") # Adds a tiny bit of vertical space before the next toggle
        
        # 3. Powerplant Toggle (Moved to the bottom)
        show_only_powerplants = st.checkbox("Only show targets containing 'powerplant' in Target Name", value=False)

        # --- Apply the Filters ---
        # Step 1: Crop by N_SAMs
        filtered_df = active_df[active_df['N_SAMs'] >= selected_min_sams].copy()
        
        # Step 2: Crop by Powerplant (if checked)
        if show_only_powerplants:
            filtered_df = filtered_df[filtered_df['Target Name'].str.contains('powerplant', case=False, na=False)]
            
        # Step 3: Crop by Target ID Prefix
        if selected_prefixes:
            prefix_mask = filtered_df['Target ID'].str.startswith(tuple(selected_prefixes), na=False)
        else:
            # If everything is unchecked (including if they just clicked "Deselect All"), show nothing
            prefix_mask = pd.Series(False, index=filtered_df.index) 
            
        # Apply the final prefix mask
        filtered_df = filtered_df[prefix_mask]

        st.divider()

        # --- Display the Data ---
        with st.expander(f"Preview {dataset_choice} Data (Showing {len(filtered_df)} targets)"):
            preview_columns = ['Target ID', 'Target Name', 'latitude', 'longitude', 'N_SAMs', 'SAM_good_quality_fraction']
            st.dataframe(filtered_df[preview_columns])
            
        # Define the required columns
        required_columns = ['Target Name', 'latitude', 'longitude', 'SAM_good_quality_fraction']
        
        # Check for missing columns in the filtered dataframe
        missing_columns = [col for col in required_columns if col not in filtered_df.columns]
        
        if missing_columns:
            st.error(f"The {dataset_choice} file is missing the following required columns: {', '.join(missing_columns)}")
        else:
            # Ensure proper data types on the filtered data
            filtered_df['latitude'] = pd.to_numeric(filtered_df['latitude'], errors='coerce')
            filtered_df['longitude'] = pd.to_numeric(filtered_df['longitude'], errors='coerce')
            filtered_df['SAM_good_quality_fraction'] = pd.to_numeric(filtered_df['SAM_good_quality_fraction'], errors='coerce')
            
            # Drop rows with invalid coordinates or ratio
            filtered_df = filtered_df.dropna(subset=['latitude', 'longitude', 'SAM_good_quality_fraction'])
            
            st.subheader("Interactive Map")

            # Generate Map using the active dataset and styling
            fig = px.scatter_mapbox(
                filtered_df,
                lat="latitude",
                lon="longitude",
                color="SAM_good_quality_fraction",
                hover_name="Target Name",
                hover_data={
                    "Target ID": True, 
                    "latitude": ':.2f', 
                    "longitude": ':.2f',
                    "N_SAMs": True,
                    #"count_GT200_soundings": ':.0f',
                    #"count_all": ':.0f',
                    "SAM_good_quality_fraction": ':.3f'
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
              height=600  
            )

            fig.update_traces(marker={"size": 12})

            # Render plot
            st.plotly_chart(fig, use_container_width=True, config={"scrollZoom": True})

    except pd.errors.ParserError:
        st.error("Error parsing one of the files. Please check if they are correctly formatted (e.g., comma-separated).")
    except Exception as e:
        st.error(f"An unexpected error occurred: {e}")


