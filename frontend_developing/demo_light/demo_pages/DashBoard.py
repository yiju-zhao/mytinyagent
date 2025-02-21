import pandas as pd
import streamlit as st
from utility.demo_util import render_button_grid
from datetime import datetime
from streamlit_option_menu import option_menu
from utility.visualization_utli import *
from utility.db_util import DataManagerContext, create_conference_statistics_df
from config import ORGANIZATION_GROUPS


class DashboardState:
    """Manages dashboard state and selections."""

    @staticmethod
    def clear_all_selections():
        """Clear all filter selections from session state."""
        for key in [
            "selected_year",
            "selected_conference",
            "selected_organization",
            "selected_keyword",
        ]:
            if key in st.session_state:
                del st.session_state[key]

    @staticmethod
    def get_current_selections():
        """Get current filter selections."""
        return {
            "year": st.session_state.get("selected_year"),
            "conference": st.session_state.get("selected_conference"),
            "organization": st.session_state.get("selected_organization"),
            "keyword": st.session_state.get("selected_keyword"),
        }


class FilterHandlers:
    """Handles different filter types and their logic."""

    @staticmethod
    def handle_year_filter():
        """Handle year-based filtering."""
        DashboardState.clear_all_selections()

        with DataManagerContext() as managers:
            # Get all available years from the database
            available_years = managers["conference"].get_all_years()
            if not available_years:
                st.error("No conference data available in the database.")
                return

            selected_year = FilterDisplay.show_year_filter(available_years)

            st.session_state.selected_year = selected_year
            st.session_state.selected_conference = None

            st.subheader(f"Conferences in {selected_year}")
            conferences = managers["conference"].get_conferences_by_year(selected_year)
            if not conferences:
                st.info(f"No conferences found for year {selected_year}")
                return

            def on_conf_click(conf):
                st.session_state.selected_conference = conf

            render_button_grid(conferences, "year", on_conf_click)

    @staticmethod
    def handle_conference_filter():
        """Handle conference-based filtering."""
        DashboardState.clear_all_selections()

        with DataManagerContext() as managers:
            conferences = managers["conference"].get_all_conferences()

            def on_conf_click(conf):
                st.session_state.selected_conference = conf
                st.session_state.selected_year = "All Years"

            render_button_grid(conferences, "all_years", on_conf_click)

    @staticmethod
    def handle_organization_filter():
        """Handle organization-based filtering."""
        DashboardState.clear_all_selections()

        with DataManagerContext() as managers:
            # Get all organizations from database that are in our tracked list
            orgs = managers["org"].get_tracked_organizations()

            # Display organizations by group
            for group_name, group_orgs in ORGANIZATION_GROUPS.items():
                # Only show groups that have organizations in our database
                filtered_orgs = [org for org in group_orgs if org in orgs]
                if filtered_orgs:
                    st.markdown(f"### 📍 {group_name}")

                    def on_org_click(org):
                        st.session_state.selected_organization = org

                    # Create a grid layout for organizations
                    cols = st.columns(2)
                    for idx, org in enumerate(sorted(filtered_orgs)):
                        with cols[idx % 2]:
                            if st.button(
                                org, key=f"org_{org}", use_container_width=True
                            ):
                                on_org_click(org)

                    st.markdown("---")

    @staticmethod
    def handle_keyword_filter():
        """Handle keyword-based filtering."""
        DashboardState.clear_all_selections()

        with DataManagerContext() as managers:
            keywords = managers["keyword"].get_all_keywords()
            search_keyword = FilterDisplay.show_keyword_search(keywords)

            if search_keyword:
                filtered_keywords = [
                    k for k in keywords if search_keyword.lower() in k.lower()
                ]

                for kw in filtered_keywords:
                    if st.button(kw, key=f"button_{kw.replace(' ', '_')}_kw"):
                        st.session_state.selected_keyword = kw


class ContentRenderers:
    """Handles rendering of different types of content."""

    @staticmethod
    def render_conference(conference: str, year: int):
        """Render conference-specific data."""
        with DataManagerContext() as managers:
            stats = managers["conference"].get_conference_stats(conference, year)
            if not stats:
                st.info(f"No data found for {conference} in {year}")
                return

            df = create_conference_statistics_df(stats)
            DashboardLayout.show_conference_layout(df, conference)

    @staticmethod
    def render_organization(organization: str):
        """Render organization-specific data."""
        with DataManagerContext() as managers:
            papers = managers["paper"].get_papers_by_organization(organization)
            if not papers:
                st.info(f"No papers found for {organization}")
                return

            papers_df = pd.DataFrame(
                [
                    {
                        "Title": p.title,
                        "Conference": p.instance_to_paper.conference_name,
                        "Year": p.year,
                        "Citations": p.citation_count,
                    }
                    for p in papers
                ]
            )

            DashboardLayout.show_conference_layout(
                papers_df.groupby(["Conference", "Year"])
                .agg({"Title": "count", "Citations": ["mean", "max"]})
                .reset_index(),
                organization,
            )

    @staticmethod
    def render_keyword(keyword: str):
        """Render keyword-specific data."""
        with DataManagerContext() as managers:
            papers = managers["paper"].get_papers_by_keyword(keyword)
            related_keywords = managers["keyword"].get_related_keywords(keyword)

            if not papers:
                st.info(f"No papers found for keyword: {keyword}")
                return

            DashboardLayout.show_keyword_layout(papers, keyword, related_keywords)

    @staticmethod
    def render_aggregate(year: int):
        """Render aggregate data for all conferences."""
        with DataManagerContext() as managers:
            stats = managers["conference"].get_yearly_conference_stats(year)
            if not stats:
                st.info(f"No data found for year {year}")
                return

            df = create_conference_statistics_df(stats, include_keywords=False)
            DashboardLayout.show_conference_layout(df, f"All Conferences - {year}")


class DashboardUI:
    """Main dashboard UI handler."""

    @staticmethod
    def render_sidebar():
        """Render sidebar with filters."""
        with st.sidebar:
            st.title("Conference Navigator")

            filter_mode = option_menu(
                menu_title=None,  # Explicitly set no title for the menu
                options=["Year", "Conference", "Organization", "Keyword"],
                icons=["calendar", "journal-text", "building", "tag"],  # Optional icons
                menu_icon="cast",
                default_index=-4,
                styles={
                    "container": {
                        "padding": "0.2rem 0",
                        "background-color": "#22222200",
                    },
                },
                key="filter_mode_menu",
            )

            if filter_mode == "Year":
                FilterHandlers.handle_year_filter()
            elif filter_mode == "Conference":
                FilterHandlers.handle_conference_filter()
            elif filter_mode == "Organization":
                FilterHandlers.handle_organization_filter()
            elif filter_mode == "Keyword":
                FilterHandlers.handle_keyword_filter()

    @staticmethod
    def render_main_content():
        """Render main content based on current selections."""
        selections = DashboardState.get_current_selections()

        if selections["year"]:
            if selections["conference"]:
                ContentRenderers.render_conference(
                    selections["conference"], selections["year"]
                )
            else:
                ContentRenderers.render_aggregate(selections["year"])
        elif selections["organization"]:
            ContentRenderers.render_organization(selections["organization"])
        elif selections["keyword"]:
            ContentRenderers.render_keyword(selections["keyword"])
        else:
            st.title("Dashboard")
            st.info("👈 Select a filter from the sidebar to view papers")


def dashboard_page():
    """Main dashboard page entry point."""
    DashboardState.clear_all_selections()
    DashboardUI.render_sidebar()
    DashboardUI.render_main_content()


if __name__ == "__main__":
    dashboard_page()
