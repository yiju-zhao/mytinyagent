import streamlit as st
import pandas as pd
from typing import List, Dict, Any, Tuple
import plotly.express as px
import plotly.graph_objects as go


class MetricsDisplay:
    """Handles display of metrics in a consistent format."""

    @staticmethod
    def show_basic_metrics(total_papers: int):
        """Display basic metrics in three columns."""
        st.metric("Total Papers", f"{total_papers:,}")
        # col1, col2, col3 = st.columns(3)
        # with col1:
        #     st.metric("Total Papers", f"{total_papers:,}")
        # with col2:
        #     st.metric("Average Citations", f"{avg_citations:.1f}")
        # with col3:
        #     st.metric("Highest Citation", f"{max_citations:,}")

    @staticmethod
    def show_conference_metrics(df: pd.DataFrame, conference: str):
        """Display conference-specific metrics."""
        st.subheader(f"{conference} Statistics")
        MetricsDisplay.show_basic_metrics(
            df["Total Papers"].sum(),
            # df["Avg Citations"].mean(),
            # df["Top Citations"].max(),
        )


class DataFrameDisplay:
    """Handles DataFrame display with consistent formatting."""

    @staticmethod
    def show_paper_table(papers_df: pd.DataFrame, use_container_width: bool = True):
        """Display paper information in a formatted table."""
        st.dataframe(
            papers_df.style.format(
                {"Citations": "{:,.0f}", "Avg Citations": "{:,.1f}"}
            ),
            use_container_width=use_container_width,
        )

    @staticmethod
    def show_conference_stats(df: pd.DataFrame):
        """Display conference statistics with formatting."""
        st.subheader("Detailed Statistics")
        DataFrameDisplay.show_paper_table(df)


class ChartDisplay:
    """Handles creation and display of various charts."""

    @staticmethod
    def show_trend_analysis(df: pd.DataFrame, x_col: str = "Year"):
        """Display trend analysis tabs with multiple charts."""
        tab1, tab2, tab3 = st.tabs(
            ["Papers Over Time", "Citations Trends", "Combined Analysis"]
        )

        with tab1:
            fig = px.line(
                df, x=x_col, y="Total Papers", title="Papers Published Over Time"
            )
            st.plotly_chart(fig, use_container_width=True)

        with tab2:
            fig = px.line(
                df,
                x=x_col,
                y=["Avg Citations", "Top Citations"],
                title="Citation Trends",
            )
            st.plotly_chart(fig, use_container_width=True)

        with tab3:
            normalized = df.copy()
            for col in ["Total Papers", "Avg Citations", "Top Citations"]:
                normalized[f"{col} (normalized)"] = (df[col] - df[col].min()) / (
                    df[col].max() - df[col].min()
                )
            fig = px.line(
                normalized,
                x=x_col,
                y=[
                    f"{col} (normalized)"
                    for col in ["Total Papers", "Avg Citations", "Top Citations"]
                ],
                title="Normalized Trends",
            )
            st.plotly_chart(fig, use_container_width=True)

    @staticmethod
    def show_conference_distribution(df: pd.DataFrame):
        """Display conference distribution charts."""
        st.subheader("Conference Distribution")
        fig = px.bar(df, x="Conference", y="Total Papers", title="Papers by Conference")
        st.plotly_chart(fig, use_container_width=True)

    @staticmethod
    def show_keyword_network(keywords: List[Tuple[str, int]], central_keyword: str):
        """Display keyword relationship network."""
        nodes = [central_keyword] + [k[0] for k in keywords]
        edges = [(central_keyword, k[0]) for k in keywords]
        weights = [k[1] for k in keywords]

        # Create network visualization using plotly
        fig = go.Figure()
        # Add nodes and edges with appropriate styling
        # (Network visualization implementation details)
        st.plotly_chart(fig, use_container_width=True)


class DashboardLayout:
    """Handles consistent layout of dashboard components."""

    @staticmethod
    def show_conference_layout(df: pd.DataFrame, conference: str):
        """Display standard conference dashboard layout."""
        MetricsDisplay.show_conference_metrics(df, conference)
        ChartDisplay.show_trend_analysis(df)
        DataFrameDisplay.show_conference_stats(df)

    @staticmethod
    def show_keyword_layout(
        papers: List[Any], keyword: str, related_keywords: List[Tuple[str, int]]
    ):
        """Display standard keyword dashboard layout."""
        papers_df = pd.DataFrame(
            [
                {
                    "Title": p.title,
                    "Authors": ", ".join([a.name for a in p.author_to_paper]),
                    "Year": p.year,
                    "Citations": p.citation_count,
                }
                for p in papers
            ]
        )

        MetricsDisplay.show_basic_metrics(
            len(papers), papers_df["Citations"].mean(), papers_df["Citations"].max()
        )

        st.subheader("Paper Distribution")
        ChartDisplay.show_trend_analysis(
            papers_df.groupby("Year")
            .agg({"Title": "count", "Citations": ["mean", "max"]})
            .reset_index()
        )

        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Related Keywords")
            ChartDisplay.show_keyword_network(related_keywords, keyword)
        with col2:
            st.subheader("Top Papers")
            DataFrameDisplay.show_paper_table(papers_df.nlargest(5, "Citations"))


class FilterDisplay:
    """Handles display of filter components."""

    @staticmethod
    def show_year_filter(years: List[int]) -> int:
        """Display year selection filter."""
        return st.selectbox("Select Year", years, index=0)

    @staticmethod
    def show_conference_filter(conferences: List[str]) -> str:
        """Display conference selection filter."""
        return st.selectbox("Select Conference", sorted(conferences), index=0)

    @staticmethod
    def show_keyword_search(keywords: List[str]) -> str:
        """Display keyword search/filter."""
        return st.text_input("Search Keywords", placeholder="Type to search...")
