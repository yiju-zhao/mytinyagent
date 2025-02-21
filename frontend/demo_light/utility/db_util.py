from sqlalchemy import func, and_, text
from typing import List, Dict, Any, Tuple, Optional
import pandas as pd
from datetime import datetime
from db_manager import DBManager
from repositories import (
    ConferenceInstanceRepository,
    PaperRepository,
    KeywordRepository,
)
from models import ConferenceInstance


class DataManagerContext:
    """Context manager for database sessions."""

    def __init__(self):
        self.db_manager = DBManager()
        self.session = None

    def __enter__(self):
        self.session = self.db_manager.get_session()
        return {
            "conference": ConferenceInstanceRepository(self.session),
            "paper": PaperRepository(self.session),
            "keyword": KeywordRepository(self.session),
        }

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            self.session.close()


def create_statistics_df(
    data: List[Any], include_keywords: bool = True
) -> pd.DataFrame:
    """Create a DataFrame from conference statistics."""
    df_data = []
    for item in data:
        row = {
            "Conference": (
                item[0] if isinstance(item[0], str) else item[0].conference_name
            ),
            "Total Papers": item[1],
            "Avg Citations": float(item[2]) if item[2] else 0,
            "Top Citations": int(item[3]) if item[3] else 0,
        }
        if include_keywords and isinstance(item[0], ConferenceInstance):
            with DataManagerContext() as managers:
                keywords = managers["keyword"].get_top_keywords_for_instance(
                    item[0].instance_id
                )
                row["Keywords"] = ", ".join(keywords)
        df_data.append(row)
    return pd.DataFrame(df_data)
