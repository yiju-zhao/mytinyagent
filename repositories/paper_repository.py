from typing import List, Optional
from venv import logger
from models import Paper, ConferenceInstance, Author, Reference, Keyword
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.inspection import inspect



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
    
    def get_papers(self, limit: Optional[int] = None, offset: Optional[int] = None, **filters) -> List[Paper]:
        """
        根据传入的过滤条件查询 Paper 表，并支持 limit 和 offset 参数。  

        参数:
            limit (int, 可选): 返回结果的最大数量。
            offset (int, 可选): 跳过的记录数（用于分页）。
            **filters: 动态关键字参数，如 title="Example", year=2024。

        返回:
            List[Paper]: 查询结果列表（可能为空列表）。
        """
        if not filters and limit is None and offset is None:
            raise ValueError("请提供至少一个查询条件或分页参数！")

        try:
            # Apply filters if they exist and are valid columns
            valid_filters = {}
            for key, value in filters.items():
                logger.info(f"key:{key}, value:{value}")
                if hasattr(Paper, key):
                    valid_filters[key] = value
                else:
                    logger.warning(f"Ignoring invalid filter field: {key}")
            
            # Start with base query
            query = self.session.query(Paper)
            if valid_filters:
                query = query.filter_by(**valid_filters)

            if offset is not None:
                query = query.offset(offset)
            if limit is not None:
                query = query.limit(limit)

            return query.all()

        except SQLAlchemyError as e:
            raise RuntimeError(f"数据库查询失败: {e}")

    def _update_relationship(self, existing_rel, new_rel):
        """
        通用关系更新函数：
        - 添加新关联
        - 移除已不存在的关联
        """
        existing_set = set(existing_rel)
        new_set = set(new_rel)

        # 添加新关联
        for item in new_set - existing_set:
            existing_rel.append(item)

        # 移除不再关联的
        for item in existing_set - new_set:
            existing_rel.remove(item)
    
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
    
    def upsert(self, paper:Paper) -> Paper:
        if not paper or not paper.title:
            raise ValueError("Invalid input: 'paper' must have a title.")

        try:
            # 根据 title 和 year 查找是否存在相同论文
            existing_paper = (
                self.session.query(Paper)
                .filter(Paper.title == paper.title, Paper.year == paper.year, Paper.instance_id==paper.instance_id)
                .first()
            )

            if existing_paper:
                # --- 基本字段更新 ---
                mapper = inspect(Paper)
                for attr in mapper.attrs:
                    if attr.key not in ['paper_id', 'author_to_paper', 'keyword_to_paper', 'reference_to_paper', 'instance_to_paper']:
                        new_value = getattr(paper, attr.key)
                        old_value = getattr(existing_paper, attr.key)
                        if new_value is not None and new_value != old_value:
                            setattr(existing_paper, attr.key, new_value)

                # --- 一对多关系 (ConferenceInstance) ---
                if paper.instance_id and paper.instance_id != existing_paper.instance_id:
                    existing_paper.instance_id = paper.instance_id

                # --- 多对多关系处理 ---
                if paper.author_to_paper:
                    self._update_relationship(existing_paper.author_to_paper, paper.author_to_paper)

                if paper.keyword_to_paper:
                    self._update_relationship(existing_paper.keyword_to_paper, paper.keyword_to_paper)

                if paper.reference_to_paper:
                    self._update_relationship(existing_paper.reference_to_paper, paper.reference_to_paper)

                self.session.add(existing_paper)
                result = existing_paper
            else:
                # 新建插入
                self.session.add(paper)
                result = paper

            self.session.commit()
            return result

        except SQLAlchemyError as e:
            self.session.rollback()
            raise RuntimeError(f"Database operation failed: {e}")
    