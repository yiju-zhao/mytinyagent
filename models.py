from datetime import datetime
from sqlalchemy import TIMESTAMP, Boolean, CheckConstraint, Column, Date, Float, Integer, String, Text, ForeignKey, UniqueConstraint, Index, ARRAY
from sqlalchemy.orm import declarative_base, relationship
from db import Base

Base = declarative_base()

class Conference(Base):
    __tablename__ = "conference"
    
    conference_id = Column(Integer, primary_key=True, autoincrement=True)  # 主键，自增
    name = Column(String(255), nullable=False, unique=True)  # 会议名称，唯一，不能为空
    type = Column(String(255), nullable=False)  # 会议类型，不能为空
    description = Column(Text)  # 会议描述，允许为空

    instances = relationship("ConferenceInstance", back_populates="conference")

    __table_args__ = (
        # 这是数据库级别的唯一约束
        UniqueConstraint('name', name='unique_conference_name'),
    )

    def __repr__(self):
        return f"<Conference(name={self.name})>"

class ConferenceInstance(Base):
    __tablename__ = "conference_instance"
    
    instance_id = Column(Integer, primary_key=True, autoincrement=True)  # 主键，自增
    name = Column(String(255), nullable=False, unique=True)  # 会议实例名称，唯一，不能为空
    conference_id = Column(Integer, ForeignKey('conference.conference_id'), nullable=False)  # 外键，关联 `conference` 表
    year = Column(Integer, nullable=False)  # 会议举办年份，不能为空
    start_date = Column(Date)  # 会议开始日期
    end_date = Column(Date)  # 会议结束日期
    location = Column(String(255))  # 会议举办地点
    website = Column(String(255))  # 会议官网链接

    # 定义与 `Conference` 表的关系
    conference = relationship("Conference", back_populates="instances")

    def __repr__(self):
        return f"<ConferenceInstance(name={self.name}， year={self.year})>"

class Paper(Base):
    __tablename__ = "paper"
    
    paper_id = Column(Integer, primary_key=True, autoincrement=True)  # 主键，自增
    instance_id = Column(Integer, ForeignKey('conference_instance.instance_id'), nullable=False)  # 外键，关联 `conference_instance` 表
    title = Column(String(255), nullable=False)  # 论文标题，不能为空
    type = Column(String(50))  # 论文类型，例如 oral, poster
    year = Column(Integer, nullable=False)  # 论文出版年份，不能为空
    publish_date = Column(Date)  # 论文发布日期
    TLDR = Column(Text)  # 论文简短总结
    abstract = Column(Text)  # 论文摘要
    content = Column(Text)  # 论文完整内容
    pdf_path = Column(String(255))  # 论文 PDF 路径或 URL
    citation_count = Column(Integer, default=0)  # 论文引用次数，默认为 0
    award = Column(String(255))  # 获奖情况（例如 best paper, best paper runner）
    doi = Column(String(255))  # Digital Object Identifier
    code_url = Column(String(255))  # 论文代码库链接
    supplementary_material_url = Column(String(255))  # 补充材料链接

    # 定义与 `ConferenceInstance` 表的关系
    instance = relationship("ConferenceInstance", backref="papers")
    # 多对多关系配置
    authors = relationship("Author", secondary="paper_authors", back_populates="papers")
    # 定义与 Keyword 表的多对多关系，通过 paper_keywords 中间表
    keywords = relationship("Keyword", secondary="paper_keywords", back_populates="papers")
    # 定义与 Reference 表的多对多关系，通过 paper_references 中间表
    references = relationship("Reference", secondary="paper_references", back_populates="papers")

    # 创建索引，方便通过标题进行快速查找
    __table_args__ = (
        Index('idx_paper_title', 'title'),
    )

    def __repr__(self):
        return f"<Paper(title={self.title}, year={self.year}, TLDR={self.TLDR})>"

class ContentEmbedding(Base):
    __tablename__ = "content_embedding"
    
    embedding_id = Column(Integer, primary_key=True, autoincrement=True)  # 自增主键
    paper_id = Column(Integer, ForeignKey('paper.paper_id'), nullable=False)  # 外键，关联 `paper` 表
    embedding = Column(ARRAY(Float), nullable=False)  # 存储 768 维的论文内容向量

    # 定义与 `Paper` 表的关系
    paper = relationship("Paper", backref="embeddings")

    # 创建 HNSW 索引
    # __table_args__ = (
    #    Index('idx_content_embedding_hnsw', 'embedding', postgresql_using='gin'),
    #)

class Author(Base):
    __tablename__ = "author"
    
    author_id = Column(Integer, primary_key=True, autoincrement=True)  # 自增主键
    name = Column(String(255), nullable=False)  # 作者名字，不能为空
    email = Column(String(255))  # 邮箱，可为空
    google_scholar_url = Column(String(255))  # Google Scholar 主页
    home_website = Column(String(255))  # 个人主页
    nationality = Column(String(100))  # 国籍
    # 多对多关系配置
    papers = relationship("Paper", secondary="paper_authors", back_populates="authors")
    # 与 Affiliation 的多对多关系
    affiliations = relationship(
        "Affiliation",  # 目标表是 Affiliation
        secondary="author_affiliation",  # 通过 author_affiliation 连接表
        back_populates="authors"  # 在 Affiliation 中定义反向关系
    )

class PaperAuthors(Base):
    __tablename__ = "paper_authors"
    
    paper_id = Column(Integer, ForeignKey('paper.paper_id'), primary_key=True)  # 外键，关联 `paper` 表
    author_id = Column(Integer, ForeignKey('author.author_id'), primary_key=True)  # 外键，关联 `author` 表
    author_order = Column(Integer, nullable=False)  # 作者排序
    is_corresponding = Column(Boolean, default=False)  # 是否为通讯作者

    # 定义与 `Paper` 和 `Author` 表的关系
    paper = relationship("Paper", back_populates="authors")
    author = relationship("Author", back_populates="papers")

class Affiliation(Base):
    __tablename__ = "affiliation"
    
    affiliation_id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)  # 组织名称
    type = Column(String(100), nullable=False)  # 类型（如 university, industry 等）
    location = Column(String(255))              # 地点
    website = Column(String(255))               # 网站
    description = Column(Text)                  # 描述

    authors = relationship(
        "Author",  # 目标表是 Author
        secondary="author_affiliation",  # 通过 author_affiliation 连接表
        back_populates="affiliations"  # 在 Author 中定义反向关系
    )

class AuthorAffiliation(Base):
    __tablename__ = "author_affiliation"
    
    author_id = Column(Integer, ForeignKey('author.author_id', ondelete='CASCADE'), primary_key=True)  # 关联作者
    affiliation_id = Column(Integer, ForeignKey('affiliation.affiliation_id', ondelete='CASCADE'), primary_key=True)  # 关联组织
    
    author = relationship("Affiliation", back_populates="authors")
    affiliation = relationship("Author", back_populates="affiliations")

# Keyword 表模型
class Keyword(Base):
    __tablename__ = 'keyword'
    
    keyword_id = Column(Integer, primary_key=True)  # 自增主键
    keyword = Column(String(255), unique=True, nullable=False)  # 关键字，不能为空，唯一
    description = Column(Text)  # 关键字的描述

    # 定义与 Paper 表的多对多关系，通过 paper_keywords 中间表
    papers = relationship("Paper", secondary="paper_keywords", back_populates="keywords")

    def __repr__(self):
        return f"<Keyword(keyword={self.keyword}, description={self.description})>"

class PaperKeyword(Base):
    __tablename__ = 'paper_keywords'

    paper_id = Column(Integer, primary_key=True)
    keyword_id = Column(Integer, primary_key=True)

    # 外键约束
    paper = relationship("Paper", back_populates="keywords")
    keyword = relationship("Keyword", back_populates="papers")

class Reference(Base):
    __tablename__ = 'reference'
    
    reference_id = Column(Integer, primary_key=True)  # 自增主键
    title = Column(String(255), nullable=False)  # 参考文献标题，不能为空
    author = Column(Text)  # 作者，多个作者用逗号分隔，可以为空
    year = Column(Integer)  # 参考文献出版年份
    journal = Column(String(255))  # 参考文献所属期刊名称
    web_url = Column(String(255))  # 参考文献的网页 URL 或指向原始论文的 URL

    # 定义与 Paper 表的多对多关系，通过 paper_references 中间表
    papers = relationship("Paper", secondary="paper_references", back_populates="references")

    def __repr__(self):
        return f"<Reference(title={self.title}, author={self.author}, year={self.year})>"

class PaperReference(Base):
    __tablename__ = 'paper_references'
    
    paper_id = Column(Integer, primary_key=True)
    reference_id = Column(Integer, primary_key=True)

    # 外键约束
    paper = relationship("Paper", back_populates="references")
    reference = relationship("Reference", back_populates="papers")
