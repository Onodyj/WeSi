"""
AI Assistant integration for context-aware website analysis assistance.
"""
from typing import Dict, List, Optional, Any
import json


class AIAssistant:
    """
    Context-aware AI assistant that uses site analysis data to provide
    custom recommendations and answer follow-up questions.
    """
    
    def __init__(self, api_key: str, model: str = "gpt-3.5-turbo"):
        """
        Initialize the AI assistant.
        
        Args:
            api_key: OpenAI API key
            model: Model to use (default: gpt-3.5-turbo)
        """
        self.api_key = api_key
        self.model = model
        self.client = None
        
        self._init_client()
    
    def _init_client(self):
        """Initialize OpenAI client."""
        try:
            import openai
            self.client = openai.OpenAI(api_key=self.api_key)
        except ImportError:
            raise ImportError(
                "OpenAI library not installed. Install with: pip install openai"
            )
        except Exception as e:
            raise ValueError(f"Failed to initialize OpenAI client: {e}")
    
    def build_context_prompt(self, analysis_data: Dict) -> str:
        """
        Build context prompt from site analysis data.
        
        Args:
            analysis_data: Complete analysis data dictionary
            
        Returns:
            Context prompt string
        """
        metadata = analysis_data.get('metadata', {})
        summary = analysis_data.get('summary', {})
        insights = analysis_data.get('insights', {})
        pages = analysis_data.get('pages', [])
        
        # Build executive summary
        domain = metadata.get('domain', 'Unknown')
        pages_count = summary.get('total_pages_analyzed', 0)
        
        # Get top issues
        critical = insights.get('critical', [])[:5]
        warnings = insights.get('warnings', [])[:5]
        recommendations = insights.get('recommendations', [])[:5]
        
        # Get sample page data
        sample_page = pages[0] if pages else {}
        sample_url = sample_page.get('url', '')
        sample_seo = sample_page.get('seo', {})
        sample_suggestions = sample_page.get('suggestions', [])[:3]
        
        context = f"""You are a website analysis expert assistant. You have just completed an analysis of {domain}.

ANALYSIS SUMMARY:
- Domain: {domain}
- Pages Analyzed: {pages_count}
- Total Images: {summary.get('total_images', 0)}
- Images without Alt: {summary.get('images_without_alt', 0)}
- Internal Links: {summary.get('total_internal_links', 0)}
- External Links: {summary.get('total_external_links', 0)}
- Broken Links: {summary.get('broken_links_found', 0)}
- Average Word Count: {summary.get('avg_word_count', 0)}

TOP CRITICAL ISSUES:
{self._format_list(critical) if critical else "None"}

TOP WARNINGS:
{self._format_list(warnings) if warnings else "None"}

TOP RECOMMENDATIONS:
{self._format_list(recommendations) if recommendations else "None"}

SAMPLE PAGE ANALYSIS ({sample_url}):
- Title: {sample_seo.get('title', 'Not set')}
- Meta Description: {sample_seo.get('meta_description', 'Not set')}
- Word Count: {sample_seo.get('word_count', 0)}

Sample Suggestions for this page:
{self._format_suggestions(sample_suggestions)}

Your role is to:
1. Answer questions about this website analysis in plain, non-technical language
2. Provide actionable recommendations that a non-technical user can understand
3. Explain technical concepts in simple terms
4. Help prioritize fixes based on impact
5. Suggest specific implementation steps when asked

Always be helpful, encouraging, and focus on practical solutions."""
        
        return context
    
    def _format_list(self, items: List[str]) -> str:
        """Format a list of items as numbered text."""
        return '\n'.join([f"{idx}. {item}" for idx, item in enumerate(items, 1)])
    
    def _format_suggestions(self, suggestions: List[Dict]) -> str:
        """Format suggestions for context prompt."""
        if not suggestions:
            return "No major issues found."
        
        lines = []
        for sugg in suggestions:
            priority = sugg.get('priority', 'medium').upper()
            issue = sugg.get('issue', '')
            suggestion = sugg.get('suggestion', '')
            lines.append(f"[{priority}] {issue}: {suggestion}")
        
        return '\n'.join(lines)
    
    def chat(
        self,
        user_message: str,
        conversation_history: List[Dict],
        analysis_data: Dict,
        system_prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send a message to the AI assistant with context.
        
        Args:
            user_message: User's question or message
            conversation_history: Previous messages in conversation
            analysis_data: Site analysis data for context
            system_prompt: Optional custom system prompt (uses context if not provided)
            
        Returns:
            Dictionary with assistant response and updated history
        """
        if not self.client:
            raise ValueError("OpenAI client not initialized")
        
        # Build system prompt with context
        if not system_prompt:
            system_prompt = self.build_context_prompt(analysis_data)
        
        # Build messages
        messages = [{"role": "system", "content": system_prompt}]
        
        # Add conversation history
        messages.extend(conversation_history)
        
        # Add current user message
        messages.append({"role": "user", "content": user_message})
        
        # Call OpenAI API
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.7,
                max_tokens=500
            )
            
            assistant_message = response.choices[0].message.content
            
            # Update conversation history
            updated_history = conversation_history + [
                {"role": "user", "content": user_message},
                {"role": "assistant", "content": assistant_message}
            ]
            
            return {
                "response": assistant_message,
                "conversation_history": updated_history,
                "usage": {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens
                }
            }
        except Exception as e:
            raise ValueError(f"OpenAI API error: {e}")
    
    def get_quick_answer(self, question: str, analysis_data: Dict) -> str:
        """
        Get a quick answer to a question without conversation history.
        
        Args:
            question: User's question
            analysis_data: Site analysis data
            
        Returns:
            Assistant's response
        """
        result = self.chat(question, [], analysis_data)
        return result['response']
    
    def generate_action_plan(self, analysis_data: Dict, focus_area: Optional[str] = None) -> str:
        """
        Generate a prioritized action plan based on analysis.
        
        Args:
            analysis_data: Site analysis data
            focus_area: Optional focus area (e.g., 'seo', 'accessibility', 'performance')
            
        Returns:
            Action plan as text
        """
        if focus_area:
            prompt = f"Create a prioritized action plan to improve {focus_area} for this website. Focus on the most impactful changes that a non-technical person can implement."
        else:
            prompt = "Create a prioritized action plan for improving this website. Focus on the most impactful changes first, and explain each step in simple terms."
        
        return self.get_quick_answer(prompt, analysis_data)
    
    def explain_issue(self, issue_description: str, analysis_data: Dict) -> str:
        """
        Get a detailed explanation of a specific issue.
        
        Args:
            issue_description: Description of the issue
            analysis_data: Site analysis data
            
        Returns:
            Explanation in plain language
        """
        prompt = f"Explain this issue in simple terms and tell me why it matters: {issue_description}"
        return self.get_quick_answer(prompt, analysis_data)
    
    def suggest_cms_specific_fix(self, issue: str, cms: str, analysis_data: Dict) -> str:
        """
        Get CMS-specific instructions for fixing an issue.
        
        Args:
            issue: Issue description
            cms: CMS name (e.g., 'squarespace', 'wordpress', 'wix')
            analysis_data: Site analysis data
            
        Returns:
            Step-by-step instructions for the specific CMS
        """
        prompt = f"The website uses {cms}. Provide step-by-step instructions for fixing this issue: {issue}. Be specific to {cms}'s interface."
        return self.get_quick_answer(prompt, analysis_data)


def store_conversation(session, site_analysis_id: int, conversation_history: List[Dict]) -> int:
    """
    Store conversation history in database.
    
    Args:
        session: SQLAlchemy session
        site_analysis_id: Site analysis ID
        conversation_history: List of message dictionaries
        
    Returns:
        Conversation ID
    """
    from we_si.models import AssistantConversation, AssistantMessage
    
    # Create conversation
    conversation = AssistantConversation(site_analysis_id=site_analysis_id)
    session.add(conversation)
    session.flush()
    
    # Add messages
    for msg in conversation_history:
        message = AssistantMessage(
            conversation_id=conversation.id,
            role=msg.get('role', 'user'),
            content=msg.get('content', '')
        )
        session.add(message)
    
    session.commit()
    return conversation.id


def load_conversation(session, conversation_id: int) -> List[Dict]:
    """
    Load conversation history from database.
    
    Args:
        session: SQLAlchemy session
        conversation_id: Conversation ID
        
    Returns:
        List of message dictionaries
    """
    from we_si.models import AssistantMessage
    
    messages = session.query(AssistantMessage).filter_by(
        conversation_id=conversation_id
    ).order_by(AssistantMessage.created_at).all()
    
    return [
        {
            "role": msg.role,
            "content": msg.content
        }
        for msg in messages
    ]


def get_site_conversations(session, site_analysis_id: int) -> List[int]:
    """
    Get all conversation IDs for a site analysis.
    
    Args:
        session: SQLAlchemy session
        site_analysis_id: Site analysis ID
        
    Returns:
        List of conversation IDs
    """
    from we_si.models import AssistantConversation
    
    conversations = session.query(AssistantConversation).filter_by(
        site_analysis_id=site_analysis_id
    ).all()
    
    return [conv.id for conv in conversations]
