import streamlit as st
import pandas as pd
from datetime import datetime


def format_timestamp(timestamp):
    """Format timestamp to a readable string."""
    return timestamp.strftime("%Y-%m-%d %H:%M")


def add_to_search_history(query, category):
    """Add a search query to the session history."""
    if "search_history" not in st.session_state:
        st.session_state.search_history = []

    search_entry = {"timestamp": datetime.now(), "query": query, "category": category}
    st.session_state.search_history.insert(0, search_entry)  # Add to start of list


def render_search_interface(in_sidebar=False):
    """Render the search interface either in main content or sidebar."""
    if in_sidebar:
        # Search box in sidebar
        search_query = st.sidebar.text_input(
            "Search Query:",
            placeholder="Enter your search query...",
            key="search_query_sidebar",
        )

        # Category selection in sidebar
        category = st.sidebar.selectbox(
            "Category",
            ["Research Papers", "People", "Companies", "Universities"],
            key="category_sidebar",
        )

        # Search button in sidebar
        if st.sidebar.button("Search", key="search_button_sidebar", type="primary"):
            if search_query:
                add_to_search_history(search_query, category)
                return True, search_query, category
    else:
        # Search box in main content
        search_query = st.text_input(
            "Search Query:",
            placeholder="Enter your search query...",
            key="search_query_main",
        )

        # Category selection in main content
        category = st.selectbox(
            "Category",
            ["Research Papers", "People", "Companies", "Universities"],
            key="category_main",
        )

        # Search button in main content
        if st.button("Search", key="search_button_main", type="primary"):
            if search_query:
                add_to_search_history(search_query, category)
                return True, search_query, category

    return False, None, None


def render_advanced_search():
    """Render the advanced search interface."""
    st.title("Advanced Search")

    # Category cards
    st.write("### Select a Category to Search")

    col1, col2 = st.columns(2)
    with col1:
        with st.expander("📚 Research Papers", expanded=True):
            st.write(
                """
            Search academic papers across multiple conferences and journals.
            - Filter by year, conference, author
            - Find related works
            - Access citations and references
            """
            )

        with st.expander("👥 People", expanded=True):
            st.write(
                """
            Find researchers and academics.
            - Search by name, institution, research area
            - View publication history
            - Find collaborators
            """
            )

    with col2:
        with st.expander("🏢 Companies", expanded=True):
            st.write(
                """
            Explore research organizations and companies.
            - Search by company name, location
            - View research focus areas
            - Track publications and patents
            """
            )

        with st.expander("🎓 Universities", expanded=True):
            st.write(
                """
            Discover academic institutions.
            - Search by name, location, department
            - View research output
            - Find collaboration opportunities
            """
            )

    # Advanced search interface
    st.write("### Search Parameters")
    return render_search_interface(in_sidebar=False)


def render_search_results(query, category):
    """Render search results based on query and category."""
    st.title(f"Search Results: {category}")
    st.write(f"Showing results for: '{query}'")

    # Example results based on category
    if category == "Research Papers":
        df = pd.DataFrame(
            {
                "Title": ["Paper 1", "Paper 2", "Paper 3"],
                "Authors": ["Author A, Author B", "Author C", "Author D, Author E"],
                "Conference": ["NeurIPS 2023", "ICML 2023", "ICLR 2023"],
                "Citations": [100, 75, 50],
                "Year": [2023, 2023, 2023],
            }
        )
    elif category == "People":
        df = pd.DataFrame(
            {
                "Name": ["John Doe", "Jane Smith", "Bob Johnson"],
                "Institution": ["Stanford", "MIT", "Berkeley"],
                "Research Areas": ["ML", "NLP", "CV"],
                "Publications": [50, 30, 40],
                "h-index": [20, 15, 18],
            }
        )
    elif category == "Companies":
        df = pd.DataFrame(
            {
                "Company": ["Tech Corp", "AI Labs", "Research Inc"],
                "Location": ["Silicon Valley", "New York", "Boston"],
                "Research Focus": ["AI", "Robotics", "NLP"],
                "Publications": [100, 75, 80],
                "Patents": [50, 30, 40],
            }
        )
    else:  # Universities
        df = pd.DataFrame(
            {
                "University": ["Stanford", "MIT", "Berkeley"],
                "Location": ["CA", "MA", "CA"],
                "Top Areas": ["AI/ML", "Robotics", "NLP"],
                "Publications": [1000, 950, 900],
                "Faculty": [200, 180, 190],
            }
        )

    # Display results with styling
    st.dataframe(df, use_container_width=True, hide_index=True)


def render_search_history():
    """Render the search history in the sidebar."""
    if "search_history" in st.session_state and st.session_state.search_history:
        st.sidebar.title("Search History")

        for entry in st.session_state.search_history:
            with st.sidebar.container():
                col1, col2 = st.sidebar.columns([3, 1])
                with col1:
                    st.write(f"🔍 {entry['query']}")
                    st.caption(
                        f"{entry['category']} • {format_timestamp(entry['timestamp'])}"
                    )
                with col2:
                    if st.button("🔄", key=f"rerun_{entry['timestamp']}"):
                        st.session_state.search_query_sidebar = entry["query"]
                        st.session_state.category_sidebar = entry["category"]
                        st.rerun()

        if st.sidebar.button("Clear History"):
            st.session_state.search_history = []
            st.rerun()


def dataset_page():
    """Main dataset page function."""
    # Initialize session state for search results
    if "has_searched" not in st.session_state:
        st.session_state.has_searched = False

    # Render search history in sidebar
    render_search_history()

    # If we've searched before, show search interface in sidebar
    if st.session_state.has_searched:
        searched, query, category = render_search_interface(in_sidebar=True)
        if searched:
            render_search_results(query, category)
        elif "last_search" in st.session_state:
            # Show last search results
            render_search_results(
                st.session_state.last_search["query"],
                st.session_state.last_search["category"],
            )
    else:
        # Show advanced search interface in main content
        searched, query, category = render_advanced_search()
        if searched:
            st.session_state.has_searched = True
            st.session_state.last_search = {"query": query, "category": category}
            st.rerun()


if __name__ == "__main__":
    dataset_page()
