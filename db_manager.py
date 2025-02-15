from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, scoped_session
from models import Base
from config import DATABASE_URL

class DBManager:
    def __init__(self, database_url=DATABASE_URL):
        """
        Initialize the DataManager by creating a SQLAlchemy engine,
        session factory, and a scoped session.
        """
        self.engine = create_engine(database_url, echo=True)
        self.session_factory = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        self.Session = scoped_session(self.session_factory)

    def get_session(self):
        """
        Return a new SQLAlchemy session.
        This session should be used within a context (or try/finally) and closed when done.
        """
        return self.Session()

    def close(self):
        """
        Remove (close) all sessions.
        This method is typically called when your application shuts down.
        """
        self.Session.remove()

    def create_tables(self):
        """
        Create all tables defined in the SQLAlchemy declarative Base.
        This is useful when setting up a new database.
        """
        Base.metadata.create_all(bind=self.engine)

    def drop_all_tables(self):
        """
        Drop all tables.
        Caution: This permanently deletes all data.
        """
        Base.metadata.drop_all(bind=self.engine)

    def reset_database(self):
        """
        Reset the database by dropping all tables and then recreating them.
        This is useful for testing or development purposes.
        """
        self.drop_all_tables()
        self.create_tables()