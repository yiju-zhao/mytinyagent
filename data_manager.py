import re
from fuzzywuzzy import fuzz
from sqlalchemy import create_engine, text, or_
from sqlalchemy.orm import sessionmaker, scoped_session
from datetime import date
from models import *
from typing import List, Dict

class DataManager:
    def __init__(self, database_url="postgresql://postgres:nasa718@localhost/test_db"):

        """Initialize DataManager with database connection"""
        self.engine = create_engine(database_url, echo=True)
        self.session_factory = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        self.Session = scoped_session(self.session_factory)

    def _clean_name(self, name: str) -> str:
        """Clean name by removing special characters and standardizing format"""
        if not name:
            return name
        
        # Convert to uppercase for standardization
        name = name.upper()
        
        # Remove special characters and extra whitespace
        name = re.sub(r'[^\w\s]', '', name)
        name = re.sub(r'\s+', ' ', name).strip()
        
        # Common abbreviation standardization
        replacements = {
            'MASSACHUSETTS INSTITUTE OF TECHNOLOGY': 'MIT',
            'MASS INST OF TECH': 'MIT',
            'MASS INSTITUTE OF TECHNOLOGY': 'MIT',
            # Add more common variations as needed
        }
        return replacements.get(name, name)
    
    def _find_best_matching_affiliation(self, name: str, affiliations: List[Affiliation], threshold: int) -> str:
        """Find the best matching affiliation using fuzzy string matching"""
        best_score = 0
        best_match = None
        
        for affiliation in affiliations:
            # Check primary name
            score = fuzz.ratio(name, affiliation.name)
            if score > best_score:
                best_score = score
                best_match = affiliation
            
            # Check aliases
            if affiliation.aliases:
                for alias in affiliation.aliases:
                    score = fuzz.ratio(name, self._clean_institution_name(alias))
                    if score > best_score:
                        best_score = score
                        best_match = affiliation
        
        return best_match if best_score >= threshold else None

    def get_session(self):
        """Return a new session instance."""
        return self.Session()

    def close(self):
        """Close all database sessions."""
        self.Session.remove()

    def clear_all_data(self):
        """Delete all data from all tables in proper dependency order."""
        session = self.get_session()
        try:
            # Order matters - delete child tables first
            tables = [
                ContentEmbedding,  # Depends on Paper
                Reference,         # Depends on Paper
                Keyword,           # Via association table (if exists)
                Paper,             # Depends on ConferenceInstance and Author
                Author,            # Depends on Affiliation (if foreign key exists)
                ConferenceInstance,# Depends on Conference
                Conference,
                Affiliation
            ]
            for table in tables:
                session.query(table).delete()
            session.commit()
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()

    def _delete_tables(self):
        """
        Delete (drop) all database tables.
        Use with caution - this will permanently delete all data and table structures.
        """
        session = self.get_session()
        try:
            # Close any existing sessions
            self.Session.remove()
            
            # Drop all tables
            # Base.metadata.drop_all(self.engine, checkfirst=True)

            # Drop all tables with CASCADE to remove dependencies
            session.execute(text("DROP SCHEMA public CASCADE;"))  # Drop the entire schema with all tables
            session.execute(text("CREATE SCHEMA public;"))  # Recreate the schema
            
            # Commit the transaction
            session.commit()
            return True
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()

    def reset_database(self):
        """
        Drop all tables and recreate them.
        Use with caution - this will permanently delete all data.
        """
        try:
            # First drop all tables
            self._delete_tables()
            
            # Then recreate all tables
            Base.metadata.create_all(self.engine)
            return True
        except Exception as e:
            raise e

    def create_tables(self):
        """Create all database tables."""
        Base.metadata.create_all(bind=self.engine)


# ----------------------------------- 新增数据 ----------------------------------- #

    def create_conference(self, name: str, type: str = "Not Defined", 
                         description: str = None) -> Conference:
        """
        Create or get a conference
        Args:
            name: Conference name
            type: Conference type
            description: Conference description
        Returns:
            Conference object
        """
        session = self.get_session()
        try:
            conference = session.query(Conference).filter_by(name=name).first()
            if conference:
                return conference
            conference = Conference(name=name, type=type, description=description)
            session.add(conference)
            session.commit()

            # Refresh to ensure we have all fields populated
            if session.is_active:
                session.refresh(conference)

            return conference
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()

    def create_conference_instance(self, name: str, conference_name: str, year: int,
                                 start_date: date, end_date: date, location: str,
                                 website: str = None) -> ConferenceInstance:
        """
        Create or get a conference instance
        Args:
            name: Instance name (e.g., "NeurIPS 2025")
            conference_name: Name of the parent conference
            year: Year of the instance
            start_date: Start date
            end_date: End date
            location: Location of the conference
            website: Conference website URL
        Returns:
            ConferenceInstance object
        """
        session = self.get_session()
        try:
            conference = session.query(Conference).filter_by(name=conference_name).first()
            if not conference:
                raise ValueError("Conference not found")

            # 检查会议实例是否已存在
            existing_instance = session.query(ConferenceInstance).filter_by(name=name, conference_id=conference.conference_id, year=year).first()
            if existing_instance:
                return existing_instance 
            
            # 创建会议实例
            instance = ConferenceInstance(name=name, conference_id=conference.conference_id, year=year, start_date=start_date, end_date=end_date, location=location, website=website)

            session.add(instance)
            session.commit()

            # Refresh or merge the instance if needed
            if session.is_active:
                session.refresh(instance)
            
            return instance
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()

    def create_affiliation(self, name: str, type: str = None, 
                          location: str = None, website: str = None,
                          description: str = None, aliases: List[str] = None) -> Affiliation:
        """
        Create or get an affiliation
        Args:
            name: Name of the affiliation (required)
            type: Type of affiliation (e.g., university, industry) (required)
            location: Location of the affiliation
            website: Website URL of the affiliation
            description: Description of the affiliation
        Returns:
            Affiliation object
        """
        session = self.get_session()
        try:
            # Clean the input name
            cleaned_name = self._clean_name(name)   
            affiliation = session.query(Affiliation).filter_by(name=name, type=type).first()

            # If no exact match, check aliases
            if not affiliation:
                affiliation = session.query(Affiliation).filter(
                or_(
                    Affiliation.aliases.contains([cleaned_name]),  # Check if cleaned_name is in aliases
                    Affiliation.name == cleaned_name
                )
            ).first()
            
            if affiliation:
                return affiliation
            
            affiliation = Affiliation(name=name, type=type, location=location,
                                      website=website, description=description, aliases=aliases or [])
            session.add(affiliation)
            session.commit()

            if session.is_active:
                session.refresh(affiliation)
            
            return affiliation
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()

    def create_author(self, author_id: str, 
                     name: str,
                     email: str = None,
                     google_scholar_url: str = None,
                     home_website: str = None,
                     nationality: str = None,
                     affiliations: List[str] = [],
                     session=None) -> Author:
        """
        Create or get an author with all their information
        Args:
            name: Author name (required)
            author_id: External source author ID (typically "~name" format)
            email: Author's email address
            google_scholar_url: URL to author's Google Scholar profile
            home_website: Author's personal website URL
            nationality: Author's nationality
            affiliation_data: List of dicts containing affiliation info
                             [{"name": "MIT", "type": "University", 
                               "location": "USA", "website": "mit.edu"}]
        Returns:
            Author object
        """
        internal_session = False
        if session is None:
            session = self.get_session()
            internal_session = True

        try:
            author = session.query(Author).filter_by(author_id=author_id).first()
            if author:
                return author
            author = Author(name=name, author_id=author_id, email=email,
                            google_scholar_url=google_scholar_url,
                            home_website=home_website, nationality=nationality)
            session.add(author)

            # 处理作者的机构信息
            if affiliations:
                for affil in affiliations:
                    existing_affiliation = session.query(Affiliation).filter(
                        or_(
                            Affiliation.name == affil,
                            Affiliation.aliases.contains([affil])
                        )
                    ).first()
                    if existing_affiliation:
                        author.affiliation_to_author.append(existing_affiliation)
                    else:
                        raise ValueError(f"Affiliation '{affil}' not found.")

            if internal_session:
                session.commit()
                session.refresh(author)
                
            return author
            
        except Exception as e:
            if internal_session:
                session.rollback()
            raise e
        finally:
            if internal_session:
                session.close()

    # 创建论文
    def create_paper(self, title: str, year: int, conference_instance_id: int, 
                    authors: List[Dict] = None, keywords: List[str] = None, 
                    references: List[Dict] = None, type: str = None, 
                    publish_date: date = None, TLDR: str = None, 
                    abstract: str = None, content: str = None, 
                    pdf_path: str = None, citation_count: int = 0, 
                    award: str = None, doi: str = None, 
                    code_url: str = None, supplementary_material_url: str = None) -> Paper:
        
        """Create a new paper with all related data in a single transaction."""
        session = self.get_session()
        try:
            instance = session.query(ConferenceInstance).get(conference_instance_id)
            if not instance:
                raise ValueError(f"Conference instance {conference_instance_id} not found")

            # Check if the paper already exists
            existing_paper = session.query(Paper).filter_by(title=title, year=year, instance_id=conference_instance_id).first()
            if existing_paper:
                return existing_paper  # Return the existing paper if found
            
            # Create the Paper object with all relevant fields
            paper = Paper(title=title, year=year, instance_id=conference_instance_id, type=type,
                          publish_date=publish_date, tldr=TLDR, abstract=abstract,
                          content=content, pdf_path=pdf_path, citation_count=citation_count,
                          award=award, doi=doi, code_url=code_url,
                          supplementary_material_url=supplementary_material_url)
            
            if authors:
                for author_data in authors:
                    author = self.create_author(
                        author_id=author_data.get('author_id'),
                        name=author_data['name'],
                        affiliations=author_data.get('affiliations', []),
                        session=session
                    )
                    paper.author_to_paper.append(author)

            if keywords:
                self.create_keywords(session, paper, keywords)

            if references:
                self.create_references(session, paper, references)

            session.add(paper)
            session.commit()
            return paper
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()

    def create_keywords(self, session, paper, keywords):
        """Create keywords for a paper."""
        for keyword in keywords:
            keyword_obj = session.query(Keyword).filter_by(keyword=keyword).first()
            if not keyword_obj:
                keyword_obj = Keyword(keyword=keyword)
                session.add(keyword_obj)
            paper.keyword_to_paper.append(keyword_obj) # 建立关系


    def create_references(self, session, paper, references):
        """Create and associate references with the paper."""
        for ref_data in references:
            existing_ref = session.query(Reference).filter_by(
                title=ref_data['title'],
                author=ref_data['author'],
                year=ref_data['year']
            ).first()
            
            if existing_ref:
                paper.reference_to_paper.append(existing_ref)  # 建立关系
            else:
                reference = Reference(
                    title=ref_data['title'],
                    author=ref_data['author'],
                    year=ref_data['year'],
                    journal=ref_data.get('journal'),
                    web_url=ref_data.get('web_url')
                )
                session.add(reference)
                paper.reference_to_paper.append(reference)  # 建立关系


# ----------------------------------- 查询数据 ----------------------------------- #

    def get_papers_by_conference(self, conference_name):
        """Get all papers from a specific conference."""
        session = self.get_session()
        try:
            return (session.query(Paper)
                    .join(ConferenceInstance)
                    .join(Conference)
                    .filter(Conference.name == conference_name)
                    .all())
        finally:
            session.close()

    # Add similar session management to other query methods...

    