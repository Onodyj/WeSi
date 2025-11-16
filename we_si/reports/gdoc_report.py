"""
Google Docs report generator.
Requires Google Docs API credentials.
"""
from typing import Dict, Optional
import os


class GoogleDocsReportGenerator:
    """
    Generates formatted Google Docs from analysis data.
    Requires Google Docs API setup with service account or OAuth.
    """
    
    def __init__(self, credentials_path: Optional[str] = None):
        """
        Initialize Google Docs generator.
        
        Args:
            credentials_path: Path to Google service account credentials JSON file
        """
        self.credentials_path = credentials_path or os.environ.get('GOOGLE_DOCS_CREDENTIALS')
        self.service = None
        
        if self.credentials_path:
            self._init_service()
    
    def _init_service(self):
        """Initialize Google Docs API service."""
        try:
            from google.oauth2 import service_account
            from googleapiclient.discovery import build
            
            SCOPES = ['https://www.googleapis.com/auth/documents']
            
            credentials = service_account.Credentials.from_service_account_file(
                self.credentials_path, scopes=SCOPES)
            
            self.service = build('docs', 'v1', credentials=credentials)
        except ImportError:
            raise ImportError(
                "Google API client not installed. Install with: "
                "pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib"
            )
        except Exception as e:
            raise ValueError(f"Failed to initialize Google Docs API: {e}")
    
    def create_document(self, title: str) -> str:
        """
        Create a new Google Doc.
        
        Args:
            title: Document title
            
        Returns:
            Document ID
        """
        if not self.service:
            raise ValueError("Google Docs service not initialized. Provide credentials.")
        
        document = self.service.documents().create(body={'title': title}).execute()
        return document.get('documentId')
    
    def generate(self, analysis_data: Dict, title: Optional[str] = None) -> str:
        """
        Generate a Google Doc report from analysis data.
        
        Args:
            analysis_data: Complete analysis data dictionary
            title: Document title (defaults to domain name)
            
        Returns:
            Document ID of created Google Doc
        """
        if not self.service:
            raise ValueError(
                "Google Docs service not initialized. Set GOOGLE_DOCS_CREDENTIALS "
                "environment variable or provide credentials_path."
            )
        
        metadata = analysis_data.get('metadata', {})
        summary = analysis_data.get('summary', {})
        insights = analysis_data.get('insights', {})
        
        # Generate title
        if not title:
            domain = metadata.get('domain', 'Unknown')
            title = f"Website Analysis Report - {domain}"
        
        # Create document
        doc_id = self.create_document(title)
        
        # Build requests for document content
        requests = []
        
        # Add header
        requests.extend(self._build_header_requests(metadata))
        
        # Add executive summary
        requests.extend(self._build_summary_requests(summary, insights))
        
        # Add statistics
        requests.extend(self._build_statistics_requests(summary))
        
        # Add insights
        requests.extend(self._build_insights_requests(insights))
        
        # Execute batch update
        if requests:
            self.service.documents().batchUpdate(
                documentId=doc_id,
                body={'requests': requests}
            ).execute()
        
        return doc_id
    
    def _build_header_requests(self, metadata: Dict) -> list:
        """Build requests for document header."""
        domain = metadata.get('domain', 'Unknown')
        base_url = metadata.get('base_url', '')
        analysis_date = metadata.get('analysis_date', 'Unknown')
        pages_crawled = metadata.get('pages_crawled', 0)
        
        return [
            {
                'insertText': {
                    'location': {'index': 1},
                    'text': f"Website Analysis Report\n{domain}\n\n"
                           f"URL: {base_url}\n"
                           f"Analysis Date: {analysis_date}\n"
                           f"Pages Crawled: {pages_crawled}\n\n"
                }
            }
        ]
    
    def _build_summary_requests(self, summary: Dict, insights: Dict) -> list:
        """Build requests for executive summary section."""
        critical = insights.get('critical', [])
        warnings = insights.get('warnings', [])
        
        text = "Executive Summary\n\n"
        text += "Top Priority Action Items:\n"
        
        for idx, item in enumerate(critical[:3], 1):
            text += f"{idx}. [CRITICAL] {item}\n"
        
        for idx, item in enumerate(warnings[:2], len(critical[:3]) + 1):
            text += f"{idx}. [WARNING] {item}\n"
        
        text += "\n"
        
        return [
            {
                'insertText': {
                    'location': {'index': 1},
                    'text': text
                }
            }
        ]
    
    def _build_statistics_requests(self, summary: Dict) -> list:
        """Build requests for statistics section."""
        text = "Key Statistics\n\n"
        text += f"Pages Analyzed: {summary.get('total_pages_analyzed', 0)}\n"
        text += f"Total Images: {summary.get('total_images', 0)}\n"
        text += f"Images without Alt: {summary.get('images_without_alt', 0)}\n"
        text += f"Internal Links: {summary.get('total_internal_links', 0)}\n"
        text += f"External Links: {summary.get('total_external_links', 0)}\n"
        text += f"Broken Links: {summary.get('broken_links_found', 0)}\n"
        text += f"Average Word Count: {summary.get('avg_word_count', 0)}\n\n"
        
        return [
            {
                'insertText': {
                    'location': {'index': 1},
                    'text': text
                }
            }
        ]
    
    def _build_insights_requests(self, insights: Dict) -> list:
        """Build requests for insights section."""
        text = "Detailed Insights\n\n"
        
        # Critical
        if insights.get('critical'):
            text += "Critical Issues:\n"
            for idx, item in enumerate(insights['critical'], 1):
                text += f"{idx}. {item}\n"
            text += "\n"
        
        # Warnings
        if insights.get('warnings'):
            text += "Warnings:\n"
            for idx, item in enumerate(insights['warnings'], 1):
                text += f"{idx}. {item}\n"
            text += "\n"
        
        # Recommendations
        if insights.get('recommendations'):
            text += "Recommendations:\n"
            for idx, item in enumerate(insights['recommendations'], 1):
                text += f"{idx}. {item}\n"
            text += "\n"
        
        # Positive
        if insights.get('positive'):
            text += "Positive Findings:\n"
            for idx, item in enumerate(insights['positive'], 1):
                text += f"{idx}. {item}\n"
            text += "\n"
        
        return [
            {
                'insertText': {
                    'location': {'index': 1},
                    'text': text
                }
            }
        ]
    
    def get_document_url(self, document_id: str) -> str:
        """
        Get the URL for a Google Doc.
        
        Args:
            document_id: Document ID
            
        Returns:
            URL string
        """
        return f"https://docs.google.com/document/d/{document_id}/edit"
