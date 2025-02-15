import ast
import pandas as pd
from datetime import datetime

from db_manager import DBManager
from repositories import (
    AuthorRepository,
    PaperRepository,
    KeywordRepository,
    ConferenceRepository,
    ConferenceInstanceRepository
)

class ConferenceAssistant:
    def __init__(
        self, 
        year:           int,
        conference:     str,
        location:       str,
        website:        str,
        category:       str,
        description:    str,
        input_file:     str,
        start_date:     datetime,
        end_date:       datetime
    ):
        self.year           = year
        self.conference     = conference
        self.start_date     = start_date
        self.end_date       = end_date
        self.location       = location
        self.website        = website
        self.category       = category
        self.description    = description
        self.csv_file_path  = input_file
        self.instance_id    = None
        self.db_manager     = DBManager()

    def upsert_conference(self):
        session = self.db_manager.get_session()
        conference_repo = ConferenceRepository(session)
        conf = conference_repo.upsert(
            name=self.conference,
            type=self.category,
            description=self.description
        )
        self.conference_id = conf.conference_id
        session.close()

    def upsert_instance(self):
        session = self.db_manager.get_session()
        instance_repo = ConferenceInstanceRepository(session)
        instance = instance_repo.upsert(
            conference_id=self.conference_id,
            name=self.conference,
            year=self.year,
            start_date=self.start_date,
            end_date=self.end_date,
            location=self.location,
            website=self.website
        )
        self.instance_id = instance.instance_id
        session.close()

    def upsert_paper(self):
        # Get a database session from the DBManager
        session = self.db_manager.get_session()
        author_repo = AuthorRepository(session)
        paper_repo = PaperRepository(session)
        keyword_repo = KeywordRepository(session)

        metadata = pd.read_csv(self.csv_file_path)
        
        # Iterate through each row in the DataFrame
        for index, row in metadata.iterrows():
            print(f"Processing row {index}...")
            if index == 10:
                break
            
            # Extract data from the row
            authorids = row["author_ids"]
            author_ids = ast.literal_eval(authorids)
            authornames = row["author_names"]
            author_names = ast.literal_eval(authornames)
            kws = row["keywords"]
            keywords = ast.literal_eval(kws)
            
            # Upsert each author
            for i in range(len(author_ids)):
                print(f"Processing author {author_ids[i]}...")
                author_repo.upsert(
                    author_id=author_ids[i],
                    name=author_names[i]
                )
            
            # Upsert each keyword
            for keyword in keywords:
                print(f"Processing keyword {keyword}...")
                keyword_repo.upsert(
                    keyword=keyword
                )
            
            # Extract paper data
            paper_title = row['paper_title']
            venue = row['venue']
            abstract = row.get('abstract', None)
            content = row.get('content', None)
            area = row.get('research_area', None)
            tldr = row.get('tldr', None)
            url = row.get('url', None)
            pdf_url = row.get('pdf_url', None)
            attachment_url = row.get('attachment_url', None)
            
            # Upsert the paper record
            paper_repo.upsert(
                title=paper_title,
                year=self.year,
                instance_id=self.instance_id,
                author_ids=author_ids,
                keywords=keywords,
                abstract=abstract,
                content=content,
                venue=venue,
                research_area=area,
                tldr=tldr,
                url=url,
                pdf_url=pdf_url,
                attachment_url=attachment_url
            )
        
        session.close()
        print("Data loaded successfully.")

    def run(self):
        self.upsert_conference()
        self.upsert_instance()
        self.upsert_paper()

