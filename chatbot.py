#!/usr/bin/env python3
"""
WeSi Chatbot Integration
Provides interactive chatbot interface for querying website analysis results.
Supports multiple LLM providers (OpenAI, Anthropic, Google, etc.)
"""

import json
import os
import sys
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any


class ChatbotInterface(ABC):
    """Abstract base class for chatbot implementations."""
    
    def __init__(self, analysis_data: Optional[Dict] = None):
        """
        Initialize chatbot with optional analysis data.
        
        Args:
            analysis_data: Website analysis report data from WeSi
        """
        self.analysis_data = analysis_data
        self.conversation_history: List[Dict[str, str]] = []
    
    @abstractmethod
    def send_message(self, message: str) -> str:
        """
        Send a message to the chatbot and get a response.
        
        Args:
            message: User's message/query
            
        Returns:
            Chatbot's response
        """
        pass
    
    def load_analysis(self, analysis_file: str):
        """Load website analysis data from JSON file."""
        try:
            with open(analysis_file, 'r', encoding='utf-8') as f:
                self.analysis_data = json.load(f)
            return True
        except Exception as e:
            print(f"Error loading analysis file: {e}")
            return False
    
    def get_system_prompt(self) -> str:
        """Generate system prompt with analysis context."""
        if not self.analysis_data:
            return (
                "You are a helpful website analysis assistant for WeSi. "
                "Answer questions about website analysis, SEO, and best practices."
            )
        
        # Create a comprehensive summary of the analysis
        metadata = self.analysis_data.get('metadata', {})
        summary = self.analysis_data.get('summary', {})
        insights = self.analysis_data.get('insights', {})
        
        prompt = f"""You are a helpful website analysis assistant for WeSi. 

You have analyzed the website: {metadata.get('base_url', 'N/A')}
Analysis date: {metadata.get('analysis_date', 'N/A')}
Pages analyzed: {metadata.get('pages_crawled', 0)}

SUMMARY STATISTICS:
- Total pages: {summary.get('total_pages_analyzed', 0)}
- Total images: {summary.get('total_images', 0)}
- Images without alt text: {summary.get('images_without_alt', 0)}
- Internal links: {summary.get('total_internal_links', 0)}
- External links: {summary.get('total_external_links', 0)}
- Broken links: {summary.get('broken_links_found', 0)}
- Average word count: {summary.get('avg_word_count', 0)}

INSIGHTS:
Critical Issues: {len(insights.get('critical', []))}
Warnings: {len(insights.get('warnings', []))}
Recommendations: {len(insights.get('recommendations', []))}
Positive Findings: {len(insights.get('positive', []))}

Critical Issues:
{chr(10).join(f"- {item}" for item in insights.get('critical', []))}

Warnings:
{chr(10).join(f"- {item}" for item in insights.get('warnings', []))}

Recommendations:
{chr(10).join(f"- {item}" for item in insights.get('recommendations', []))}

You can answer questions about:
- SEO optimization and best practices
- Content quality and improvements
- Technical issues found during analysis
- Specific page details (structure, headings, images, links)
- Actionable recommendations for improvement

Be helpful, clear, and provide actionable advice based on the analysis data.
"""
        return prompt
    
    def format_page_info(self, page_url: str) -> str:
        """Format detailed information about a specific page."""
        if not self.analysis_data or 'pages' not in self.analysis_data:
            return "No analysis data available."
        
        # Find the page in the analysis
        page = None
        for p in self.analysis_data['pages']:
            if p['url'] == page_url or page_url in p['url']:
                page = p
                break
        
        if not page:
            return f"Page not found in analysis: {page_url}"
        
        info = f"PAGE ANALYSIS: {page['url']}\n\n"
        info += f"Status Code: {page.get('status_code', 'N/A')}\n"
        info += f"Word Count: {page.get('seo', {}).get('word_count', 0)}\n\n"
        
        # SEO info
        seo = page.get('seo', {})
        info += f"SEO:\n"
        info += f"  Title: {seo.get('title', 'N/A')} ({seo.get('title_length', 0)} chars)\n"
        info += f"  Meta Description: {seo.get('meta_description', 'N/A')[:100]}... ({seo.get('meta_description_length', 0)} chars)\n\n"
        
        # Structure
        structure = page.get('structure', {})
        info += f"HTML Structure:\n"
        info += f"  Semantic elements: {', '.join(structure.get('semantic_elements_used', []))}\n\n"
        
        # Images
        images = page.get('images', {})
        info += f"Images: {images.get('count', 0)} total, {images.get('missing_alt_count', 0)} missing alt text\n\n"
        
        # Links
        links = page.get('links', {})
        info += f"Links: {links.get('total_internal', 0)} internal, {links.get('total_external', 0)} external\n"
        
        # Broken links
        broken = page.get('broken_links', [])
        if broken:
            info += f"\nBroken Links: {len(broken)}\n"
            for link in broken[:3]:
                info += f"  - {link.get('url', 'N/A')} (Status: {link.get('status_code', 'N/A')})\n"
        
        return info


class OpenAIChatbot(ChatbotInterface):
    """OpenAI GPT chatbot implementation."""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-3.5-turbo", 
                 analysis_data: Optional[Dict] = None):
        """
        Initialize OpenAI chatbot.
        
        Args:
            api_key: OpenAI API key (or set OPENAI_API_KEY env var)
            model: Model to use (gpt-3.5-turbo, gpt-4, etc.)
            analysis_data: Website analysis data
        """
        super().__init__(analysis_data)
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        self.model = model
        
        if not self.api_key:
            raise ValueError(
                "OpenAI API key required. Set OPENAI_API_KEY environment variable "
                "or pass api_key parameter."
            )
        
        try:
            import openai
            self.client = openai.OpenAI(api_key=self.api_key)
        except ImportError:
            raise ImportError(
                "OpenAI package not installed. Install with: pip install openai"
            )
    
    def send_message(self, message: str) -> str:
        """Send message to OpenAI and get response."""
        # Add system message with context
        messages = [{"role": "system", "content": self.get_system_prompt()}]
        
        # Add conversation history
        messages.extend(self.conversation_history)
        
        # Add current message
        messages.append({"role": "user", "content": message})
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.7,
                max_tokens=1000
            )
            
            assistant_message = response.choices[0].message.content
            
            # Update conversation history
            self.conversation_history.append({"role": "user", "content": message})
            self.conversation_history.append({"role": "assistant", "content": assistant_message})
            
            # Keep history manageable (last 10 exchanges)
            if len(self.conversation_history) > 20:
                self.conversation_history = self.conversation_history[-20:]
            
            return assistant_message
        
        except Exception as e:
            return f"Error communicating with OpenAI: {e}"


class AnthropicChatbot(ChatbotInterface):
    """Anthropic Claude chatbot implementation."""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "claude-3-sonnet-20240229",
                 analysis_data: Optional[Dict] = None):
        """
        Initialize Anthropic chatbot.
        
        Args:
            api_key: Anthropic API key (or set ANTHROPIC_API_KEY env var)
            model: Model to use (claude-3-sonnet-20240229, etc.)
            analysis_data: Website analysis data
        """
        super().__init__(analysis_data)
        self.api_key = api_key or os.getenv('ANTHROPIC_API_KEY')
        self.model = model
        
        if not self.api_key:
            raise ValueError(
                "Anthropic API key required. Set ANTHROPIC_API_KEY environment variable "
                "or pass api_key parameter."
            )
        
        try:
            import anthropic
            self.client = anthropic.Anthropic(api_key=self.api_key)
        except ImportError:
            raise ImportError(
                "Anthropic package not installed. Install with: pip install anthropic"
            )
    
    def send_message(self, message: str) -> str:
        """Send message to Anthropic and get response."""
        # Add conversation history
        messages = []
        messages.extend(self.conversation_history)
        messages.append({"role": "user", "content": message})
        
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1000,
                system=self.get_system_prompt(),
                messages=messages
            )
            
            assistant_message = response.content[0].text
            
            # Update conversation history
            self.conversation_history.append({"role": "user", "content": message})
            self.conversation_history.append({"role": "assistant", "content": assistant_message})
            
            # Keep history manageable (last 10 exchanges)
            if len(self.conversation_history) > 20:
                self.conversation_history = self.conversation_history[-20:]
            
            return assistant_message
        
        except Exception as e:
            return f"Error communicating with Anthropic: {e}"


class GoogleChatbot(ChatbotInterface):
    """Google Gemini chatbot implementation."""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "gemini-pro",
                 analysis_data: Optional[Dict] = None):
        """
        Initialize Google Gemini chatbot.
        
        Args:
            api_key: Google API key (or set GOOGLE_API_KEY env var)
            model: Model to use (gemini-pro, etc.)
            analysis_data: Website analysis data
        """
        super().__init__(analysis_data)
        self.api_key = api_key or os.getenv('GOOGLE_API_KEY')
        self.model = model
        
        if not self.api_key:
            raise ValueError(
                "Google API key required. Set GOOGLE_API_KEY environment variable "
                "or pass api_key parameter."
            )
        
        try:
            import google.generativeai as genai
            genai.configure(api_key=self.api_key)
            self.client = genai.GenerativeModel(self.model)
            self.chat = self.client.start_chat(history=[])
        except ImportError:
            raise ImportError(
                "Google Generative AI package not installed. "
                "Install with: pip install google-generativeai"
            )
    
    def send_message(self, message: str) -> str:
        """Send message to Google Gemini and get response."""
        try:
            # Prepend system context to first message
            if not self.conversation_history:
                message = self.get_system_prompt() + "\n\nUser: " + message
            
            response = self.chat.send_message(message)
            assistant_message = response.text
            
            # Update conversation history
            self.conversation_history.append({"role": "user", "content": message})
            self.conversation_history.append({"role": "assistant", "content": assistant_message})
            
            # Keep history manageable
            if len(self.conversation_history) > 20:
                self.conversation_history = self.conversation_history[-20:]
            
            return assistant_message
        
        except Exception as e:
            return f"Error communicating with Google Gemini: {e}"


def create_chatbot(provider: str = "openai", api_key: Optional[str] = None,
                  model: Optional[str] = None, analysis_data: Optional[Dict] = None) -> ChatbotInterface:
    """
    Factory function to create chatbot instances.
    
    Args:
        provider: Chatbot provider (openai, anthropic, google)
        api_key: API key for the provider
        model: Model name to use
        analysis_data: Website analysis data
        
    Returns:
        ChatbotInterface instance
    """
    provider = provider.lower()
    
    if provider == "openai":
        return OpenAIChatbot(
            api_key=api_key,
            model=model or "gpt-3.5-turbo",
            analysis_data=analysis_data
        )
    elif provider == "anthropic":
        return AnthropicChatbot(
            api_key=api_key,
            model=model or "claude-3-sonnet-20240229",
            analysis_data=analysis_data
        )
    elif provider == "google":
        return GoogleChatbot(
            api_key=api_key,
            model=model or "gemini-pro",
            analysis_data=analysis_data
        )
    else:
        raise ValueError(
            f"Unknown provider: {provider}. "
            "Supported providers: openai, anthropic, google"
        )


def interactive_chat_session(chatbot: ChatbotInterface):
    """Run an interactive chat session with the chatbot."""
    print("\n" + "="*70)
    print("WeSi Chatbot - Interactive Mode")
    print("="*70)
    print("Type your questions about the website analysis.")
    print("Commands: 'quit', 'exit', 'help'")
    print("="*70 + "\n")
    
    while True:
        try:
            user_input = input("You: ").strip()
            
            if not user_input:
                continue
            
            if user_input.lower() in ['quit', 'exit', 'bye']:
                print("\nGoodbye! 👋")
                break
            
            if user_input.lower() == 'help':
                print("\nYou can ask questions like:")
                print("- What are the critical issues found?")
                print("- How can I improve my SEO?")
                print("- Tell me about the images on my site")
                print("- What pages are missing meta descriptions?")
                print("- Give me a summary of the analysis")
                print("- How's my content quality?")
                print()
                continue
            
            # Get response from chatbot
            response = chatbot.send_message(user_input)
            print(f"\nAssistant: {response}\n")
        
        except KeyboardInterrupt:
            print("\n\nGoodbye! 👋")
            break
        except Exception as e:
            print(f"\nError: {e}\n")


def main():
    """Main entry point for chatbot CLI."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="WeSi Chatbot - Interactive assistant for website analysis"
    )
    parser.add_argument(
        '--provider',
        choices=['openai', 'anthropic', 'google'],
        default='openai',
        help='Chatbot provider to use (default: openai)'
    )
    parser.add_argument(
        '--model',
        help='Model name to use (provider-specific)'
    )
    parser.add_argument(
        '--analysis',
        help='Path to website analysis JSON file'
    )
    parser.add_argument(
        '--api-key',
        help='API key for the provider (or set via environment variable)'
    )
    
    args = parser.parse_args()
    
    # Load analysis data if provided
    analysis_data = None
    if args.analysis:
        try:
            with open(args.analysis, 'r', encoding='utf-8') as f:
                analysis_data = json.load(f)
            print(f"Loaded analysis from: {args.analysis}")
        except Exception as e:
            print(f"Warning: Could not load analysis file: {e}")
            print("Continuing without analysis data...\n")
    
    # Create chatbot
    try:
        chatbot = create_chatbot(
            provider=args.provider,
            api_key=args.api_key,
            model=args.model,
            analysis_data=analysis_data
        )
    except Exception as e:
        print(f"Error creating chatbot: {e}")
        sys.exit(1)
    
    # Start interactive session
    interactive_chat_session(chatbot)


if __name__ == '__main__':
    main()
