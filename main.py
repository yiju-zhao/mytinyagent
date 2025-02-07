import logging
from typing import Optional
from pathlib import Path
import click
from openreview_client import OpenReviewClient
from pdf_processor import PDFProcessor
from data_manager import DataManager
from analytics import PaperAnalytics
from config import config
import os

# Set up logging
logging.basicConfig(
    level=logging.DEBUG if config.debug_mode else logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ResearchPaperAgent:
    def __init__(self):
        self.openreview = OpenReviewClient()
        self.pdf_processor = PDFProcessor()
        self.data_manager = DataManager()
        self.analytics = PaperAnalytics()
    
    def process_conference_papers(self):
        """Main workflow to process papers from a conference"""
        try:
            # Fetch papers from OpenReview
            for paper_data in self.openreview.get_conference_papers():
                logger.info(f"Processing paper: {paper_data['title']}")
                
                try:
                    # Extract additional metadata from PDF
                    if paper_data['pdf_url']:
                        metadata = self.pdf_processor.process_paper(
                            paper_data['openreview_id'],
                            paper_data['pdf_url']
                        )
                        # Update paper data with extracted metadata
                        paper_data.update(metadata)
                    
                    # Store paper data
                    self.data_manager.add_paper(paper_data)
                    
                except Exception as e:
                    logger.error(f"Error processing paper {paper_data['openreview_id']}: {str(e)}")
                    continue
            
            # Run analytics
            self._generate_reports()
            
        except Exception as e:
            logger.error(f"Workflow error: {str(e)}")
            raise
        
        finally:
            self._cleanup()
    
    def _generate_reports(self):
        """Generate analytics reports"""
        try:
            # Get trending topics
            trends = self.analytics.get_trending_topics()
            logger.info("Trending Topics:")
            for trend in trends:
                logger.info(f"- {trend['topic']} ({trend['paper_count']} papers)")
            
            # Get affiliation stats
            stats = self.analytics.get_affiliation_stats()
            logger.info("\nPapers by Affiliation:")
            for aff, count in sorted(stats.items(), key=lambda x: x[1], reverse=True):
                logger.info(f"- {aff}: {count} papers")
            
            # Get collaboration patterns
            collabs = self.analytics.get_author_collaborations()
            logger.info("\nTop Collaborators:")
            for collab in sorted(collabs, key=lambda x: x['collaborator_count'], reverse=True)[:10]:
                logger.info(
                    f"- {collab['author']}: {collab['collaborator_count']} collaborators, "
                    f"{collab['paper_count']} papers"
                )
            
        except Exception as e:
            logger.error(f"Error generating reports: {str(e)}")
    
    def _cleanup(self):
        """Clean up resources"""
        self.data_manager.close()
        self.analytics.close()

@click.command()
@click.option('--conference', help='Conference name to process')
def main(conference: Optional[str]):
    """Main entry point"""
    if conference:
        config.openreview.conference = conference
    
    if not config.openreview.conference:
        raise click.UsageError("Conference name must be provided")
    
    agent = ResearchPaperAgent()
    agent.process_conference_papers()

if __name__ == '__main__':
    main() 