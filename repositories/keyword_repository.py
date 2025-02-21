from models import Keyword, Paper, PaperKeyword
from sqlalchemy import func, text, and_


class KeywordRepository:
    def __init__(self, session):
        self.session = session

    def upsert(self, keyword: str, description: str = "") -> Keyword:
        keyword_obj = self.session.query(Keyword).filter_by(keyword=keyword).first()
        if keyword_obj:
            setattr(keyword_obj, description, description)
        else:
            keyword_obj = Keyword(keyword=keyword, description=description)
            self.session.add(keyword_obj)

        self.session.commit()
        return keyword_obj

    def get_all_keywords(self) -> list[str]:
        """Get all available keywords."""
        keywords = self.session.query(Keyword.keyword).distinct().all()
        return sorted([kw[0] for kw in keywords])

    def get_top_keywords_for_instance(
        self, instance_id: int, limit: int = 5
    ) -> list[str]:
        """Get top keywords for a conference instance."""
        keywords = (
            self.session.query(
                Keyword.keyword, func.count(PaperKeyword.c.paper_id).label("count")
            )
            .join(PaperKeyword)
            .join(Paper)
            .filter(Paper.instance_id == instance_id)
            .group_by(Keyword.keyword)
            .order_by(text("count DESC"))
            .limit(limit)
            .all()
        )
        return [k[0] for k in keywords]

    def get_related_keywords(
        self, keyword: str, limit: int = 5
    ) -> list[tuple[str, int]]:
        """Get related keywords based on co-occurrence."""
        return (
            self.session.query(
                Keyword.keyword,
                func.count(PaperKeyword.c.paper_id).label("co_occurrence"),
            )
            .join(PaperKeyword)
            .join(Paper)
            .join(PaperKeyword, Paper.paper_id == PaperKeyword.c.paper_id)
            .join(
                Keyword,
                and_(
                    PaperKeyword.c.keyword_id == Keyword.keyword_id,
                    Keyword.keyword != keyword,
                ),
            )
            .group_by(Keyword.keyword)
            .order_by(text("co_occurrence DESC"))
            .limit(limit)
            .all()
        )
