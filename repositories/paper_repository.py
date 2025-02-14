from models import Paper, ConferenceInstance, Author, Reference, Keyword

class PaperRepository:
    def __init__(self, session):
        self.session = session

    def _get_author(self, author_id: str) -> Author:
        author = self.session.query(Author).filter_by(author_id=author_id).first()
        if not author:
            raise ValueError(f"Author {author_id} not found.")
        return author
    
    def _get_reference(self, title: str) -> Reference:
        reference = self.session.query(Reference).filter_by(title=title).first()
        if not reference:
            raise ValueError(f"Reference {title} not found.")
        return reference
    
    def _get_keyword(self, keyword: str) -> Keyword:
        keyword = self.session.query(Keyword).filter_by(keyword=keyword).first()
        if not keyword:
            raise ValueError(f"Keyword {keyword} not found.")
        return keyword


    def upsert(self, title: str, year: int, instance_id: str, author_ids: list = None, references: list = None, keywords: list = None, **kwargs) -> Paper:

        paper = self.session.query(Paper).filter_by(instance_id=instance_id, title=title).first()
        if paper:
            for key, value in kwargs.items():
                setattr(paper, key, value)
        else:
            paper = Paper(instance_id=instance_id, title=title, year=year, **kwargs)
            self.session.add(paper)

        if author_ids:
            paper.author_to_paper = []
            for authorid in author_ids:
                author_obj = self._get_author(author_id=authorid)
                paper.author_to_paper.append(author_obj)
        if references:
            paper.reference_to_paper = []
            for reference in references:
                reference_obj = self._get_reference(title=reference["title"])
                paper.reference_to_paper.append(reference_obj)
        if keywords:
            paper.keyword_to_paper = []
            for kw in keywords:
                keyword_obj = self._get_keyword(keyword=kw)
                paper.keyword_to_paper.append(keyword_obj)

        self.session.commit()
        return paper
    