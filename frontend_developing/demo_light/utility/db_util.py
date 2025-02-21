import sys
from pathlib import Path
# Add the parent directory to sys.path to access db_manager.py
sys.path.append(str(Path(__file__).parents[3]))

import pandas as pd
from db_manager import DBManager  # This will now find the root db_manager.py
from models import ConferenceInstance
from repositories import ConferenceInstanceRepository, PaperRepository, KeywordRepository, AffiliationRepository


class DataManagerContext:
    """Context manager for database sessions."""

    def __init__(self):
        self.data_manager = DBManager()
        self.session = None

    def __enter__(self):
        self.session = self.data_manager.get_session()
        return {
            "conference": ConferenceInstanceRepository(self.session),
            "paper": PaperRepository(self.session),
            "keyword": KeywordRepository(self.session),
            "org": AffiliationRepository(self.session),
        }

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            self.session.close()


def create_conference_statistics_df(
    data: list[any], include_keywords: bool = True
) -> pd.DataFrame:
    """Create a DataFrame from conference statistics."""
    df_data = []
    for item in data:
        row = {
            "Conference": (
                item[0] if isinstance(item[0], str) else item[0].conference_name
            ),
            "Total Papers": item[1],
        }
        if include_keywords and isinstance(item[0], ConferenceInstance):
            with DataManagerContext() as managers:
                keywords = managers["keyword"].get_top_keywords_for_instance(
                    item[0].instance_id
                )
                row["Keywords"] = ", ".join(keywords)
        df_data.append(row)
    return pd.DataFrame(df_data)
