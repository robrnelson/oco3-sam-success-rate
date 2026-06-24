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
    #df['row_success_rate'] = df['N Good Quality Soundings'] / df['N L2 Soundings'].replace(0, pd.NA)

    # I actually want N Good Quality Soundings / N Total Soundings
    # Going to approximate N Total Soundings = 2880 to save everyone some work
    df['row_success_rate'] = df['N Good Quality Soundings'] / 2880 #.replace(0, pd.NA)
   
    # NEW: Save a copy of the raw data we need for the time series
    raw_df = df[['Target ID', 'Target Name', 'Start Time', 'row_success_rate']].copy()
    raw_df['Start Time'] = pd.to_datetime(raw_df['Start Time'], errors='coerce') # Ensure it is a datetime
 
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
   
    df_grouped_renamed = df_grouped.rename(columns={
        'Median Latitude': 'latitude',
        'Median Longitude': 'longitude',       
        'N Good Quality Soundings': 'count_GT200_soundings',
        'N L2 Soundings': 'count_all',
        'row_success_rate': 'SAM_good_quality_fraction',
        'Start Time': 'N_SAMs'                 
    })
    
    return raw_df, df_grouped_renamed # <--- Return both!
 

def process_sif_data(df):
    df.columns = df.columns.str.strip()
    #df['Site Latitude'] = df['Site Latitude'].replace(-999, pd.NA)
    #df['Site Longitude'] = df['Site Longitude'].replace(-999, pd.NA)
    #df['row_success_rate'] = df['N Good Soundings'] / df['Total Soundings'].replace(0, pd.NA)
    df['row_success_rate'] = df['N Good Soundings'] / 2880 #.replace(0, pd.NA)

    # NEW: Save a copy of the raw data we need for the time series
    raw_df = df[['Target ID', 'Target Name', 'Start Time', 'row_success_rate']].copy()
    raw_df['Start Time'] = pd.to_datetime(raw_df['Start Time'], errors='coerce') # Ensure it is a datetime
    
    df_grouped = df.groupby('Target ID').agg({
        'Target Name': 'first',
        'Site Latitude': 'mean',
        'Site Longitude': 'mean',
        'N Good Soundings': 'sum',
        'Total Soundings': 'sum',
        'row_success_rate': 'mean',
        'Start Time': 'count'
    }).reset_index()
   
    df_grouped_renamed = df_grouped.rename(columns={
        'Site Latitude': 'latitude',
        'Site Longitude': 'longitude',
        'N Good Soundings': 'count_GT200_soundings',
        'Total Soundings': 'count_all',
        'row_success_rate': 'SAM_good_quality_fraction',
        'Start Time': 'N_SAMs'                 
    })
    
    return raw_df, df_grouped_renamed # <--- Return both!
 

st.set_page_config(page_title="OCO-3 SAM Good Quality Retrieval Fraction Map Viewer", layout="wide")
#st.title("OCO-3 SAM Success Rate Map Viewer")
st.title("OCO-3 SAM Good Quality Retrieval Fraction Map Viewer")

# Check if both hard-coded files actually exist
if not os.path.exists(FILE_PATH) or not os.path.exists(SIF_FILE_PATH):
    st.error(f"Missing files. Please ensure both `{FILE_PATH}` and `{SIF_FILE_PATH}` are in the correct location.")
else:
    try:
        # Read the files
        raw_df_co2 = pd.read_csv(FILE_PATH, sep=',', engine='python')
        raw_df_sif = pd.read_csv(SIF_FILE_PATH, sep=',', engine='python')
      
        # Process the raw files using their specific functions
        raw_co2, df_co2 = process_co2_data(raw_df_co2)
        raw_sif, df_sif = process_sif_data(raw_df_sif)
        #df_co2 = process_co2_data(raw_df_co2)
        #df_sif = process_sif_data(raw_df_sif)

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
            active_raw_df = raw_co2
            active_colorscale = px.colors.sequential.Viridis
            active_title = "SAM Locations Colored by the Mean Fraction of Good Quality CO2 Retrievals (N Good Quality Soundings / N Total Soundings)"
        else:
            active_df = df_sif
            active_raw_df = raw_sif
            active_colorscale = px.colors.sequential.Viridis
            active_title = "SAM Locations Colored by the Mean Fraction of Good Quality SIF Retrievals (N Good Quality Soundings / N Total Soundings)"

        st.divider() # Adds a clean visual line to separate toggles from filters

        # --- Filtering UI ---
        st.write("### Data Filters")
        
        # Target ID Prefix Checkboxes
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
        
        # Powerplant Toggle (Moved to the bottom)
        show_only_powerplants = st.checkbox("Power plants", value=False)

        # N_SAMs Slider
        min_possible = int(active_df['N_SAMs'].min())
        max_possible = int(active_df['N_SAMs'].max())
        
        selected_min_sams = st.slider(
            "Minimum N_SAMs:",
            min_value=min_possible,
            max_value=max_possible,
            value=min_possible,
            step=1
        )

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

            # --- Map Layout & Styling ---
            # Create two columns: a wide one for the title, a narrow one for the slider
            map_title_col, slider_col = st.columns([6, 1]) 
            
            with map_title_col:
                st.subheader("Interactive Map")
                
            with slider_col:
                selected_color_range = st.slider(
                    "Color Range:",
                    min_value=0.0,
                    max_value=1.0,
                    value=(0.0, 0.8),
                    step=0.05
                )
            
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
                #range_color=[0, 1],
                range_color=selected_color_range,
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
            #st.plotly_chart(fig, use_container_width=True, config={"scrollZoom": True})

            # Render plot and capture click events (Requires Streamlit 1.35+)
            map_event = st.plotly_chart(
                fig, 
                use_container_width=True, 
                config={"scrollZoom": True},
                on_select="rerun"  # <--- Tells Streamlit to rerun the app when a dot is clicked!
            )

            st.divider()

            # --- Site Deep Dive (Time Series) ---
            st.subheader("Individual Site Success Rate Over Time")
            
            # Get the list of Target IDs that survived our current filters
            #available_targets = sorted(filtered_df['Target ID'].unique())
            available_targets = sorted(filtered_df['Target Name'].unique())
            
            if available_targets:
                # --- Map Click Logic ---
                default_index = 0  # By default, show the first target in the list
               
                # Check if the user clicked a point on the map
                if map_event and len(map_event.selection.get("points", [])) > 0:
                    
                    # Extract the dictionary of data for the clicked point
                    point_data = map_event.selection["points"][0]
                    
                    # Safely grab the index (Streamlit uses point_index, Plotly natively uses pointIndex)
                    clicked_point_index = point_data.get("point_index") or point_data.get("pointIndex")
                    
                    if clicked_point_index is not None:
                        # Use .iloc to find the matching row in our filtered dataframe
                        #clicked_target_id = filtered_df.iloc[clicked_point_index]['Target ID']
                        clicked_target_id = filtered_df.iloc[clicked_point_index]['Target Name']
                        
                        # Find where that target lives in our dropdown list and update the default index
                        if clicked_target_id in available_targets:
                            default_index = available_targets.index(clicked_target_id) 
  
                # -----------------------
                # The dropdown now defaults to whatever was clicked on the map (or the first item)
                selected_target = st.selectbox(
                    "Select a Target Name (or click a site on the map above):", 
                    available_targets,
                    index=default_index # <--- Syncs with the map click
                )
                
                # Filter our raw dataframe for only that target
                target_time_data = active_raw_df[active_raw_df['Target Name'] == selected_target].dropna(subset=['Start Time', 'row_success_rate'])
                
                if not target_time_data.empty:
                    # Generate the time series scatter plot
                    fig_time = px.scatter(
                        target_time_data,
                        x="Start Time",
                        y="row_success_rate",
                        title=f"Individual SAM Success Rates for {selected_target}",
                        labels={"row_success_rate": "Row Success Rate", "Start Time": "Observation Date"},
                        hover_data={
                            "Target ID": True, 
                            "Target Name": True,
                            "Start Time": "|%Y-%m-%d %H:%M:%S"
                        }
                    )
                    
                    fig_time.update_traces(marker={"size": 8, "opacity": 0.7})
                    fig_time.update_layout(yaxis_range=[-0.05, 1.05]) 
                    
                    st.plotly_chart(fig_time, use_container_width=True)
                else:
                    st.warning("No valid time data available for this target.")


    except pd.errors.ParserError:
        st.error("Error parsing one of the files. Please check if they are correctly formatted (e.g., comma-separated).")
    except Exception as e:
        st.error(f"An unexpected error occurred: {e}")


