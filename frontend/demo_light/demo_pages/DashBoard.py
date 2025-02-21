import pandas as pd
import streamlit as st
from streamlit_option_menu import option_menu
from datetime import datetime


def clear_all_selections():
    """Clear all filter selections from session state."""
    if 'selected_year' in st.session_state:
        del st.session_state.selected_year
    if 'selected_conference' in st.session_state:
        del st.session_state.selected_conference
    if 'selected_organization' in st.session_state:
        del st.session_state.selected_organization
    if 'selected_keyword' in st.session_state:
        del st.session_state.selected_keyword

def render_button_grid(items, key_suffix, callback, num_columns=2):
    """Render a grid of buttons from a list of items.
    
    Parameters:
      items (list): List of strings to render as buttons.
      key_suffix (str): A suffix for the unique button keys.
      callback (function): Function to call when a button is clicked.
      num_columns (int): Number of columns to display.
    """
    columns = st.columns(num_columns)
    chunk_size = (len(items) + num_columns - 1) // num_columns
    for i, col in enumerate(columns):
        with col:
            start = i * chunk_size
            end = (i + 1) * chunk_size
            for item in items[start:end]:
                if st.button(item, key=f"{item}_{key_suffix}", use_container_width=True):
                    callback(item)


def handle_year_filter():
    clear_all_selections()
    current_year = datetime.now().year
    selected_year = st.selectbox("Select Year", range(current_year, current_year - 10, -1), index=0)
    st.session_state.selected_year = selected_year

    # Clear any previous conference/organization selection
    st.session_state.selected_conference = None
    st.session_state.pop("selected_organization", None)

    st.subheader(f"Conferences in {selected_year}")
    conferences = ["NeurIPS", "ICML", "ICLR", "AAAI", "IJCAI"]

    def on_conf_click(conf):
        st.session_state.selected_conference = conf

    render_button_grid(conferences, key_suffix="year", callback=on_conf_click)

def handle_conference_filter():
    clear_all_selections()
    st.subheader("Select Conference")
    conferences = sorted([
        "NeurIPS", "ICML", "ICLR", "AAAI", "IJCAI", 
        "CVPR", "ICCV", "ECCV", "ACL", "EMNLP", "NAACL"
    ])

    def on_conf_click(conf):
        st.session_state.selected_conference = conf
        st.session_state.selected_year = "All Years"

    render_button_grid(conferences, key_suffix="all_years", callback=on_conf_click)

def handle_organization_filter():
    clear_all_selections()
    st.subheader("Select Organization")
    organizations = sorted([
        "Stanford University", "MIT", "Carnegie Mellon University",
        "UC Berkeley", "Google Research", "DeepMind",
        "Microsoft Research", "OpenAI", "Facebook AI Research", "IBM Research"
    ])

    def on_org_click(org):
        st.session_state.selected_organization = org
        st.session_state.selected_year = "All Years"
        st.session_state.pop("selected_conference", None)
        st.session_state.pop("selected_year", None)

    render_button_grid(organizations, key_suffix="org", callback=on_org_click)

def handle_keyword_filter():
    clear_all_selections()
    st.subheader("Search by Keyword")
    search_keyword = st.text_input("Enter keyword:", placeholder="Type to search...")
    
    if search_keyword:
        keywords = [
            "Machine Learning", "Deep Learning", "Natural Language Processing",
            "Computer Vision", "Reinforcement Learning", "Neural Networks",
            "Artificial Intelligence", "Transformers", "GANs", "Optimization"
        ]
        # Filter and sort keywords
        filtered = sorted([kw for kw in keywords if search_keyword.lower() in kw.lower()])
        
        # CSS for button styling
        st.markdown("""
            <style>
            div[data-testid="stButton"] > button {
                width: 100%;
                margin: 5px 0;
                border: 1px solid var(--primary-color);
                transition: all 0.3s ease;
            }
            </style>
        """, unsafe_allow_html=True)
        
        for kw in filtered:
            is_selected = st.session_state.get("selected_keyword") == kw
            if is_selected:
                button_style = f"""
                    <style>
                        div[data-testid="stButton"] > button[data-testid="button_{kw.replace(" ", "_")}_kw"] {{
                            background-color: var(--primary-color) !important;
                            color: white !important;
                        }}
                    </style>
                """
                st.markdown(button_style, unsafe_allow_html=True)
            if st.button(kw, key=f"button_{kw.replace(' ', '_')}_kw", use_container_width=True, type="secondary"):
                st.session_state.selected_keyword = kw
                # Clear conference and year selections when a keyword is chosen
                # st.session_state.pop("selected_conference", None)
                # st.session_state.pop("selected_year", None)
            st.write("")

def render_conference_data(conference: str, year: int):
    """Render historical data for a specific conference across years."""
    if year == "All Years":
        st.header(f"{conference}")
    else:
        st.header(f"{conference} - {year}")

    df = pd.DataFrame({
        "Year": [2024, 2023, 2022, 2021, 2020],
        "Total Papers": [150, 140, 130, 120, 110],
        "Avg Citations": [45, 50, 55, 60, 65],
        "Top Citations": [500, 550, 600, 650, 700],
        "Keywords": ["ML, AI", "DL, RL", "NLP, CV", "Planning", "Knowledge"]
    })
    
    total_papers = df["Total Papers"].sum()
    avg_citations = df["Avg Citations"].mean()
    max_citations = df["Top Citations"].max()
    
    st.subheader(f"{conference} Statistics")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Papers", f"{total_papers:,}")
    with col2:
        st.metric("Average Citations", f"{avg_citations:.1f}")
    with col3:
        st.metric("Highest Citation", f"{max_citations:,}")
    
    st.subheader("Year-wise Statistics")
    years = df["Year"].tolist()
    metrics_per_row = 3
    num_rows = (len(years) + metrics_per_row - 1) // metrics_per_row
    
    for row in range(num_rows):
        cols = st.columns(metrics_per_row)
        for col_idx in range(metrics_per_row):
            idx = row * metrics_per_row + col_idx
            if idx < len(years):
                with cols[col_idx]:
                    row_data = df.iloc[idx]
                    st.markdown(f"### {row_data['Year']}")
                    st.metric("Papers", row_data["Total Papers"])
                    st.metric("Avg Citations", row_data["Avg Citations"])
                    st.metric("Top Citation", row_data["Top Citations"])
    
    st.subheader("Historical Data")
    st.dataframe(df)
    
    st.subheader("Trends")
    tab1, tab2, tab3 = st.tabs(["Papers Over Time", "Citations Trends", "Combined Analysis"])
    with tab1:
        st.line_chart(df.set_index("Year")[["Total Papers"]])
    with tab2:
        st.line_chart(df.set_index("Year")[["Avg Citations", "Top Citations"]])
    with tab3:
        normalized = df.copy()
        for col in ["Total Papers", "Avg Citations", "Top Citations"]:
            normalized[f"{col} (normalized)"] = (df[col] - df[col].min()) / (df[col].max() - df[col].min())
        norm_data = normalized[["Year", "Total Papers (normalized)", "Avg Citations (normalized)", "Top Citations (normalized)"]]
        st.line_chart(norm_data.set_index("Year"))
        st.caption("Normalized trends for comparing relative changes")

# def render_conference_data(conf: str, year: int):
#     st.header(f"{conf} - {year}")
#     df = pd.DataFrame({
#         "Conference": [conf] * 3,
#         "Title": ["Paper 1", "Paper 2", "Paper 3"],
#         "Authors": ["Author A", "Author B", "Author C"],
#         "Citations": [100, 50, 25],
#         "Keywords": ["ML, AI", "NLP, Transform", "CV, CNN"],
#     })
#     st.dataframe(df)

def render_organization_data(organization: str):
    st.header(f"Papers from {organization}")
    df = pd.DataFrame({
        "Year": [2024, 2023, 2022, 2021, 2020],
        "Conference": ["NeurIPS", "ICML", "ICLR", "AAAI", "IJCAI"],
        "Total Papers": [15, 12, 18, 10, 14],
        "Avg Citations": [45, 50, 55, 40, 48],
        "Top Citations": [500, 450, 600, 350, 480],
    })
    
    total_papers = df["Total Papers"].sum()
    avg_citations = df["Avg Citations"].mean()
    max_citations = df["Top Citations"].max()
    
    st.subheader("Overall Statistics")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Papers", f"{total_papers:,}")
    with col2:
        st.metric("Average Citations", f"{avg_citations:.1f}")
    with col3:
        st.metric("Highest Citation", f"{max_citations:,}")
    
    st.subheader("Conference Distribution")
    conf_dist = df.groupby("Conference")["Total Papers"].sum().reset_index()
    st.bar_chart(conf_dist.set_index("Conference"))
    
    st.subheader("Publication Trends")
    tab1, tab2 = st.tabs(["Papers by Year", "Citations Trends"])
    with tab1:
        year_papers = df.groupby("Year")["Total Papers"].sum().reset_index()
        st.line_chart(year_papers.set_index("Year"))
    with tab2:
        st.line_chart(df.set_index("Year")[["Avg Citations", "Top Citations"]])
    
    st.subheader("Recent Papers")
    recent_papers = pd.DataFrame({
        "Title": ["Paper Title 1", "Paper Title 2", "Paper Title 3", "Paper Title 4", "Paper Title 5"],
        "Conference": ["NeurIPS 2024", "ICML 2023", "ICLR 2023", "AAAI 2023", "IJCAI 2023"],
        "Citations": [100, 80, 75, 60, 50],
        "Authors": [
            "Author1, Author2", "Author3, Author4", 
            "Author5, Author6", "Author7, Author8", "Author9, Author10"
        ]
    })
    st.dataframe(recent_papers, use_container_width=True)

def render_keyword_data(keyword: str):
    st.header(f"Papers about {keyword}")
    df = pd.DataFrame({
        "Year": [2024, 2023, 2022, 2021, 2020],
        "Papers Count": [250, 200, 180, 150, 120],
        "Avg Citations": [40, 45, 50, 55, 60],
        "Top Citations": [800, 750, 700, 650, 600],
    })
    
    total_papers = df["Papers Count"].sum()
    avg_citations = df["Avg Citations"].mean()
    max_citations = df["Top Citations"].max()
    
    st.subheader("Overall Statistics")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Papers", f"{total_papers:,}")
    with col2:
        st.metric("Average Citations", f"{avg_citations:.1f}")
    with col3:
        st.metric("Highest Citation", f"{max_citations:,}")
    
    st.subheader("Trend Analysis")
    tab1, tab2, tab3 = st.tabs(["Publication Trend", "Citations Impact", "Related Keywords"])
    with tab1:
        st.line_chart(df.set_index("Year")["Papers Count"])
    with tab2:
        st.line_chart(df.set_index("Year")[["Avg Citations", "Top Citations"]])
    with tab3:
        related = pd.DataFrame({
            "Keyword": ["Related1", "Related2", "Related3", "Related4", "Related5"],
            "Co-occurrence": [80, 65, 50, 45, 40],
            "Correlation": [0.85, 0.75, 0.70, 0.65, 0.60]
        })
        st.dataframe(related, use_container_width=True)
    
    st.subheader("Top Papers")
    top_papers = pd.DataFrame({
        "Title": [f"Top Paper about {keyword} {i}" for i in range(1, 6)],
        "Conference": ["NeurIPS 2024", "ICML 2023", "ICLR 2023", "AAAI 2023", "IJCAI 2023"],
        "Citations": [800, 750, 700, 650, 600],
        "Authors": [
            "Author1, Author2", "Author3, Author4",
            "Author5, Author6", "Author7, Author8", "Author9, Author10"
        ]
    })
    st.dataframe(top_papers, use_container_width=True)
    
    st.subheader("Conference Distribution")
    conf_dist = pd.DataFrame({
        "Conference": ["NeurIPS", "ICML", "ICLR", "AAAI", "IJCAI"],
        "Papers": [50, 45, 40, 35, 30],
        "Percentage": ["25%", "22.5%", "20%", "17.5%", "15%"]
    })
    st.dataframe(conf_dist, use_container_width=True)

def render_aggregate_data(year: int):
    st.header(f"All Conferences - {year}")
    df = pd.DataFrame({
        "Conference": ["NeurIPS", "ICML", "ICLR", "AAAI", "IJCAI"],
        "Total Papers": [150, 120, 100, 80, 90],
        "Avg Citations": [45, 38, 42, 35, 40],
        "Top Citations": [500, 450, 400, 350, 380],
        "Keywords": ["ML, AI", "DL, RL", "NLP, CV", "Planning", "Knowledge"]
    })

    total_papers = df["Total Papers"].sum()
    avg_citations = (df["Total Papers"] * df["Avg Citations"]).sum() / total_papers
    max_citations = df["Top Citations"].max()

    st.subheader("Overall Statistics")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Papers", f"{total_papers:,}")
    with col2:
        st.metric("Average Citations", f"{avg_citations:.1f}")
    with col3:
        st.metric("Highest Citation", f"{max_citations:,}")

    st.subheader("Conference-wise Statistics")
    conferences = df["Conference"].tolist()
    metrics_per_row = 3
    num_rows = (len(conferences) + metrics_per_row - 1) // metrics_per_row

    for row in range(num_rows):
        cols = st.columns(metrics_per_row)
        for col_idx in range(metrics_per_row):
            idx = row * metrics_per_row + col_idx
            if idx < len(conferences):
                with cols[col_idx]:
                    st.markdown(f"### {conferences[idx]}")
                    st.metric("Papers", df.iloc[idx]["Total Papers"])
                    st.metric("Avg Citations", df.iloc[idx]["Avg Citations"])
                    st.metric("Top Citation", df.iloc[idx]["Top Citations"])

    st.subheader("Detailed Conference Data")
    st.dataframe(df)
    st.subheader("Visualizations")
    tab1, tab2 = st.tabs(["Papers Distribution", "Citations Analysis"])
    with tab1:
        st.bar_chart(df.set_index("Conference")[["Total Papers"]])
    with tab2:
        st.line_chart(df.set_index("Conference")[["Avg Citations", "Top Citations"]])

import streamlit as st
from streamlit_option_menu import option_menu

def render_sidebar():
    with st.sidebar:
        st.title("Conference Navigator")
        filter_mode = option_menu(
            menu_title=None,  # Explicitly set no title for the menu
            options=["Year", "Conference", "Organization", "Keyword"],
            icons=["calendar", "journal-text", "building", "tag"],  # Optional icons
            menu_icon="cast",
            default_index=-4,
            styles={"container": {"padding": "0.2rem 0", "background-color": "#22222200"},},
            key="filter_mode_menu"
        )
        # st.divider()
        if filter_mode == "Year":
            handle_year_filter()
        elif filter_mode == "Conference":
            handle_conference_filter()
        elif filter_mode == "Organization":
            handle_organization_filter()
        elif filter_mode == "Keyword":
            handle_keyword_filter()


def render_main_content():
    year = st.session_state.get("selected_year")
    conf = st.session_state.get("selected_conference")
    org = st.session_state.get("selected_organization")
    keyword = st.session_state.get("selected_keyword")
    
    if year:
        if conf:
            render_conference_data(conf, year)
        else:
            render_aggregate_data(year)
    elif org:
        render_organization_data(org)
    elif keyword:
        render_keyword_data(keyword)
    else:
        st.title("Dashboard")
        st.info("👈 Select a filter from the sidebar to view papers")

def dashboard_page():
    clear_all_selections()
    render_sidebar()
    render_main_content()
    # render_advanced_search()

if __name__ == "__main__":
    dashboard_page()
