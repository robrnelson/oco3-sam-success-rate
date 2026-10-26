import streamlit as st
import pandas as pd
import plotly.express as px
import os

# --- Configuration ---
#FILE_PATH = "OCO3_SAM_GT200_ratios.txt"
FILE_PATH = "sam_co2_stats_Fisher_20260617.csv"
#SIF_FILE_PATH = "OCO3_SAM_GT200_SIF_ratios.txt"
SIF_FILE_PATH = "sam_sif_stats2_Fisher_20260617.csv"
GOOD_SOUNDING_THRESHOLD = 200   # a SAM "counts" if it has more than this many good soundings
TOTAL_SOUNDINGS = 2880          # approximate N Total Soundings per SAM
# ---------------------

# Design tokens (light theme; matches .streamlit/config.toml)
INK = "#0b0b0b"
INK_SECONDARY = "#52514e"
INK_MUTED = "#898781"
GRID = "#e1e0d9"
SURFACE = "#fcfcfb"
ACCENT = "#2a78d6"
FONT_FAMILY = "system-ui, -apple-system, 'Segoe UI', sans-serif"


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
    df['row_success_rate'] = df['N Good Quality Soundings'] / TOTAL_SOUNDINGS #.replace(0, pd.NA)

    # Save a copy of the raw data we need for the time series
    raw_df = df[['Target ID', 'Target Name', 'Start Time', 'N Good Quality Soundings', 'row_success_rate']].copy()
    raw_df = raw_df.rename(columns={'N Good Quality Soundings': 'n_good'})
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
    df['row_success_rate'] = df['N Good Soundings'] / TOTAL_SOUNDINGS #.replace(0, pd.NA)

    # Save a copy of the raw data we need for the time series
    raw_df = df[['Target ID', 'Target Name', 'Start Time', 'N Good Soundings', 'row_success_rate']].copy()
    raw_df = raw_df.rename(columns={'N Good Soundings': 'n_good'})
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


def style_figure(fig):
    """Applies the shared, quiet chart styling."""
    fig.update_layout(
        template="plotly_white",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"family": FONT_FAMILY, "size": 14, "color": INK_SECONDARY},
        hoverlabel={"bgcolor": SURFACE, "bordercolor": GRID, "font": {"family": FONT_FAMILY, "color": INK}},
    )
    return fig


CUSTOM_CSS = f"""
<style>
    .block-container {{ padding-top: 2.2rem; padding-bottom: 3rem; max-width: 1400px; }}
    header[data-testid="stHeader"] {{ background: transparent; }}

    .app-title {{ font-size: 2rem; font-weight: 700; letter-spacing: -0.02em; color: {INK}; margin: 0; line-height: 1.15; }}
    .app-subtitle {{ font-size: 1rem; color: {INK_SECONDARY}; margin: 0.35rem 0 1.4rem 0; }}

    .section-label {{ font-size: 0.78rem; font-weight: 600; letter-spacing: 0.06em; text-transform: uppercase; color: {INK_MUTED}; margin: 0 0 0.25rem 0; }}

    div[data-testid="stMetric"] {{
        background: {SURFACE};
        border: 1px solid {GRID};
        border-radius: 14px;
        padding: 1rem 1.25rem;
    }}
    div[data-testid="stMetricLabel"] p {{ color: {INK_SECONDARY}; font-size: 0.9rem; }}
    div[data-testid="stMetricValue"] {{ font-size: 2.6rem; font-weight: 650; letter-spacing: -0.02em; color: {INK}; }}

    section[data-testid="stSidebar"] {{ border-right: 1px solid {GRID}; }}
    section[data-testid="stSidebar"] h3 {{ font-size: 1.05rem; letter-spacing: -0.01em; }}
    div[data-testid="stExpander"] {{ border-radius: 14px; border-color: {GRID}; }}
    div[data-testid="stPlotlyChart"] {{ border-radius: 12px; }}
    hr {{ margin: 1.4rem 0; border-color: {GRID}; }}
</style>
"""


st.set_page_config(page_title="OCO-3 SAM Good Quality Retrieval Fraction", page_icon="🛰️", layout="wide")
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)
st.markdown(
    '<p class="app-title">OCO-3 SAM Good Quality Retrieval Fraction</p>'
    '<p class="app-subtitle">Explore how often Snapshot Area Map (SAM) soundings yield good quality retrievals, by site and over time.</p>',
    unsafe_allow_html=True,
)

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

        # --- Sidebar: dataset + filters ---
        with st.sidebar:
            st.markdown("### Variable")
            dataset_choice = st.radio(
                "Variable to display",
                options=["CO2", "SIF"],
                horizontal=True,
                label_visibility="collapsed",
            )

            # Set variables based on the user's choice
            if dataset_choice == "CO2":
                active_df = df_co2
                active_raw_df = raw_co2
                active_colorscale = px.colors.sequential.Viridis
            else:
                active_df = df_sif
                active_raw_df = raw_sif
                active_colorscale = px.colors.sequential.Viridis
            active_title = (
                f"SAM locations colored by the mean fraction of good quality {dataset_choice} retrievals "
                "(N good quality soundings / N total soundings)"
            )

            st.divider()
            st.markdown("### Filters")

            # Target ID Prefix Checkboxes
            st.caption("Include Target IDs starting with")
            target_prefixes = ["C40", "cal", "coccon", "desert", "ecostress", "fossil", "sif", "tccon", "texmex", "val", "volcano"]

            # The Deselect All checkbox
            deselect_all = st.checkbox("Deselect all", value=False)

            cols = st.columns(2)
            selected_prefixes = []

            for i, prefix in enumerate(target_prefixes):
                with cols[i % 2]:
                    # By tying the key to the deselect_all state, Streamlit will completely reset
                    # the checkboxes whenever you toggle "Deselect all", avoiding state conflicts!
                    if st.checkbox(prefix, value=not deselect_all, key=f"{prefix}_{deselect_all}"):
                        selected_prefixes.append(prefix)

            st.divider()

            # Powerplant Toggle
            show_only_powerplants = st.toggle("Power plants only", value=False)

            # N_SAMs Slider
            min_possible = int(active_df['N_SAMs'].min())
            max_possible = int(active_df['N_SAMs'].max())

            selected_min_sams = st.slider(
                "Minimum N_SAMs",
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
            # If everything is unchecked (including if they just clicked "Deselect all"), show nothing
            prefix_mask = pd.Series(False, index=filtered_df.index)

        # Apply the final prefix mask
        filtered_df = filtered_df[prefix_mask]

        # --- Display the Data ---
        with st.expander(f"Preview {dataset_choice} data ({len(filtered_df):,} targets)"):
            preview_columns = ['Target ID', 'Target Name', 'latitude', 'longitude', 'N_SAMs', 'SAM_good_quality_fraction']
            st.dataframe(filtered_df[preview_columns], use_container_width=True, hide_index=True)

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

            # --- Map ---
            with st.container(border=True):
                map_title_col, slider_col = st.columns([3, 1], vertical_alignment="bottom")

                with map_title_col:
                    st.markdown('<p class="section-label">Map</p>', unsafe_allow_html=True)
                    st.subheader("Interactive map")
                    st.caption(active_title)

                with slider_col:
                    selected_color_range = st.slider(
                        "Color range",
                        min_value=0.0,
                        max_value=1.0,
                        value=(0.0, 0.8),
                        step=0.05
                    )

                fig = px.scatter_map(
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
                        "SAM_good_quality_fraction": ':.3f'
                    },
                    color_continuous_scale=active_colorscale,
                    range_color=selected_color_range,
                    zoom=1,
                    center={"lat": 0, "lon": 0},
                    map_style='carto-positron',
                    labels={"SAM_good_quality_fraction": "Good fraction"},
                )
                style_figure(fig)
                fig.update_layout(
                    margin={"r": 0, "t": 8, "l": 0, "b": 0},
                    height=600,
                    coloraxis_colorbar={
                        "title": {"text": "Good fraction", "side": "top"},
                        "thickness": 12,
                        "len": 0.6,
                        "outlinewidth": 0,
                        "tickfont": {"size": 12},
                    },
                )
                fig.update_traces(marker={"size": 12})

                # Render plot and capture click events (Requires Streamlit 1.35+)
                map_event = st.plotly_chart(
                    fig,
                    use_container_width=True,
                    config={"scrollZoom": True, "displayModeBar": False},
                    on_select="rerun"  # <--- Tells Streamlit to rerun the app when a dot is clicked!
                )

            # --- Site Deep Dive (Time Series) ---
            with st.container(border=True):
                st.markdown('<p class="section-label">Site detail</p>', unsafe_allow_html=True)
                st.subheader("Fraction of good retrievals over time")

                # Get the list of Target Names that survived our current filters
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
                            clicked_target_id = filtered_df.iloc[clicked_point_index]['Target Name']

                            # Find where that target lives in our dropdown list and update the default index
                            if clicked_target_id in available_targets:
                                default_index = available_targets.index(clicked_target_id)

                    # The dropdown defaults to whatever was clicked on the map (or the first item)
                    selected_target = st.selectbox(
                        "Select a target (or click a site on the map above)",
                        available_targets,
                        index=default_index # <--- Syncs with the map click
                    )

                    # Filter our raw dataframe for only that target
                    target_time_data = active_raw_df[active_raw_df['Target Name'] == selected_target].dropna(subset=['Start Time', 'row_success_rate'])

                    if not target_time_data.empty:
                        # --- SAM counts for the selected location ---
                        n_total_sams = len(target_time_data)
                        n_good_sams = int((target_time_data['n_good'] > GOOD_SOUNDING_THRESHOLD).sum())

                        metric_a, metric_b, _ = st.columns([1, 1, 2])
                        metric_a.metric(
                            f"SAMs with >{GOOD_SOUNDING_THRESHOLD} good soundings",
                            f"{n_good_sams:,}",
                        )
                        metric_b.metric(
                            "Total SAMs",
                            f"{n_total_sams:,}",
                            help=f"All SAMs observed at {selected_target}, regardless of how many good soundings they have.",
                        )

                        # Generate the time series scatter plot
                        fig_time = px.scatter(
                            target_time_data,
                            x="Start Time",
                            y="row_success_rate",
                            title=f"Good quality fractions for {selected_target}",
                            labels={"row_success_rate": "SAM good quality fraction", "Start Time": "Observation date"},
                            hover_data={
                                "Target ID": True,
                                "Target Name": True,
                                "n_good": ':,',
                                "Start Time": "|%Y-%m-%d %H:%M:%S"
                            }
                        )
                        style_figure(fig_time)

                        # 2px surface ring keeps overlapping dots legible
                        fig_time.update_traces(
                            marker={"size": 9, "color": ACCENT, "opacity": 0.9,
                                    "line": {"width": 2, "color": SURFACE}}
                        )
                        fig_time.update_layout(
                            yaxis_range=[-0.05, 1.05],
                            height=460,
                            margin={"t": 56, "r": 24, "l": 8, "b": 8},
                            title={"font": {"size": 16, "color": INK}, "x": 0, "xanchor": "left"},
                        )

                        # Reference line: the fraction that corresponds to the good-sounding threshold
                        fig_time.add_hline(
                            y=GOOD_SOUNDING_THRESHOLD / TOTAL_SOUNDINGS,
                            line={"color": INK_MUTED, "width": 1},
                            annotation_text=f"{GOOD_SOUNDING_THRESHOLD} good soundings",
                            annotation_position="top left",
                            annotation_font={"size": 12, "color": INK_SECONDARY},
                        )

                        # Month ticks with recessive hairline grid
                        fig_time.update_xaxes(
                            dtick="M1",
                            tickformat="%b %Y",
                            showgrid=True,
                            gridcolor=GRID,
                            gridwidth=1,
                            linecolor=GRID,
                            tickangle=90,
                            tickfont={"size": 12, "color": INK_MUTED},
                            title_font={"size": 14},
                        )
                        fig_time.update_yaxes(
                            showgrid=True,
                            gridcolor=GRID,
                            gridwidth=1,
                            zeroline=False,
                            tickfont={"size": 12, "color": INK_MUTED},
                            title_font={"size": 14},
                        )

                        st.plotly_chart(fig_time, use_container_width=True, config={"displaylogo": False})

                    else:
                        st.warning("No valid time data available for this target.")
                else:
                    st.info("No targets match the current filters.")


    except pd.errors.ParserError:
        st.error("Error parsing one of the files. Please check if they are correctly formatted (e.g., comma-separated).")
    except Exception as e:
        st.error(f"An unexpected error occurred: {e}")
