#!/usr/bin/env python3
"""
Example usage of WeSi Chatbot Integration
Demonstrates how to use the chatbot programmatically.
"""

import json
from chatbot import ChatbotInterface, create_chatbot


# Define MockChatbot for examples that don't require API keys
class MockChatbot(ChatbotInterface):
    """Mock chatbot for testing without API keys."""
    
    def send_message(self, message: str) -> str:
        self.conversation_history.append({"role": "user", "content": message})
        
        message_lower = message.lower()
        
        if not self.analysis_data:
            response = "No analysis data loaded."
        elif "summary" in message_lower:
            summary = self.analysis_data.get('summary', {})
            response = f"Summary: {summary.get('total_pages_analyzed', 0)} pages analyzed"
        elif "critical" in message_lower:
            insights = self.analysis_data.get('insights', {})
            critical = insights.get('critical', [])
            response = "Critical issues:\n" + "\n".join(f"- {i}" for i in critical) if critical else "No critical issues"
        elif "fix" in message_lower or "improve" in message_lower:
            response = "To fix issues: 1) Add title tags 2) Add meta descriptions 3) Fix broken links"
        else:
            response = f"Received: {message}"
        
        self.conversation_history.append({"role": "assistant", "content": response})
        return response


def example_1_basic_usage():
    """Example 1: Basic chatbot usage with analysis data."""
    print("\n" + "="*70)
    print("Example 1: Basic Chatbot Usage")
    print("="*70)
    
    # Load an existing analysis report
    with open('test_analysis.json', 'r') as f:
        analysis_data = json.load(f)
    
    # Create a mock chatbot (for testing without API keys)
    # In production, use: create_chatbot('openai', analysis_data=analysis_data)
    chatbot = MockChatbot(analysis_data=analysis_data)
    
    # Ask questions
    print("\nUser: Give me a summary of the analysis")
    response = chatbot.send_message("Give me a summary of the analysis")
    print(f"Assistant: {response}")
    
    print("\nUser: What are the critical issues?")
    response = chatbot.send_message("What are the critical issues?")
    print(f"Assistant: {response}")
    
    print("\n✓ Example 1 complete\n")


def example_2_custom_chatbot():
    """Example 2: Creating a custom chatbot implementation."""
    print("\n" + "="*70)
    print("Example 2: Custom Chatbot Implementation")
    print("="*70)
    
    class SimpleChatbot(ChatbotInterface):
        """Simple custom chatbot that echoes messages."""
        
        def send_message(self, message: str) -> str:
            """Echo the message back with analysis context."""
            self.conversation_history.append({"role": "user", "content": message})
            
            if self.analysis_data:
                summary = self.analysis_data.get('summary', {})
                response = (f"Echo: {message}\n"
                           f"Context: Analyzed {summary.get('total_pages_analyzed', 0)} pages")
            else:
                response = f"Echo: {message}"
            
            self.conversation_history.append({"role": "assistant", "content": response})
            return response
    
    # Create and use custom chatbot
    with open('test_analysis.json', 'r') as f:
        analysis_data = json.load(f)
    
    custom_bot = SimpleChatbot(analysis_data=analysis_data)
    
    print("\nUser: Hello custom bot!")
    response = custom_bot.send_message("Hello custom bot!")
    print(f"Assistant: {response}")
    
    print("\n✓ Example 2 complete\n")


def example_3_programmatic_analysis_and_chat():
    """Example 3: Run analysis and immediately chat about results."""
    print("\n" + "="*70)
    print("Example 3: Programmatic Analysis + Chat")
    print("="*70)
    
    from wesi import WebsiteAnalyzer
    
    # Note: This will fail without network access, but shows the pattern
    print("\nThis example shows how to programmatically:")
    print("1. Run website analysis")
    print("2. Get the report")
    print("3. Create a chatbot with the results")
    print("4. Query the chatbot")
    
    print("\nCode pattern:")
    print("""
    # Run analysis
    analyzer = WebsiteAnalyzer("https://example.com", max_pages=10)
    analyzer.crawl()
    report = analyzer.generate_report()
    
    # Create chatbot with results
    chatbot = create_chatbot('openai', analysis_data=report)
    
    # Query the chatbot
    response = chatbot.send_message("What SEO improvements should I make?")
    print(response)
    """)
    
    print("\n✓ Example 3 complete\n")


def example_4_multi_provider():
    """Example 4: Using different AI providers."""
    print("\n" + "="*70)
    print("Example 4: Multi-Provider Support")
    print("="*70)
    
    print("\nWeSi chatbot supports multiple AI providers:")
    print("\n1. OpenAI (GPT):")
    print("   chatbot = create_chatbot('openai', model='gpt-4')")
    print("   Requires: pip install openai")
    print("   Env var: OPENAI_API_KEY")
    
    print("\n2. Anthropic (Claude):")
    print("   chatbot = create_chatbot('anthropic', model='claude-3-sonnet-20240229')")
    print("   Requires: pip install anthropic")
    print("   Env var: ANTHROPIC_API_KEY")
    
    print("\n3. Google (Gemini):")
    print("   chatbot = create_chatbot('google', model='gemini-pro')")
    print("   Requires: pip install google-generativeai")
    print("   Env var: GOOGLE_API_KEY")
    
    print("\nTo use any provider:")
    print("1. Install the provider's package")
    print("2. Set the API key environment variable")
    print("3. Create chatbot with provider name")
    
    print("\n✓ Example 4 complete\n")


def example_5_context_management():
    """Example 5: Working with conversation context."""
    print("\n" + "="*70)
    print("Example 5: Conversation Context Management")
    print("="*70)
    
    with open('test_analysis.json', 'r') as f:
        analysis_data = json.load(f)
    
    chatbot = MockChatbot(analysis_data=analysis_data)
    
    # Have a conversation
    print("\nHaving a multi-turn conversation:")
    
    messages = [
        "What's the summary?",
        "What about critical issues?",
        "How can I fix them?",
    ]
    
    for msg in messages:
        print(f"\nUser: {msg}")
        response = chatbot.send_message(msg)
        print(f"Assistant: {response[:100]}...")  # Truncate for display
    
    print(f"\nConversation history has {len(chatbot.conversation_history)} messages")
    print("The chatbot maintains context across the conversation")
    
    print("\n✓ Example 5 complete\n")


def example_6_error_handling():
    """Example 6: Error handling and fallbacks."""
    print("\n" + "="*70)
    print("Example 6: Error Handling")
    print("="*70)
    
    print("\nGood practices for error handling:")
    
    print("\n1. Handle missing analysis data:")
    print("""
    try:
        with open('analysis.json', 'r') as f:
            data = json.load(f)
    except FileNotFoundError:
        print("Run analysis first!")
        sys.exit(1)
    """)
    
    print("\n2. Handle API key errors:")
    print("""
    try:
        chatbot = create_chatbot('openai')
    except ValueError as e:
        print(f"API key error: {e}")
        print("Set OPENAI_API_KEY environment variable")
    """)
    
    print("\n3. Handle provider errors:")
    print("""
    try:
        chatbot = create_chatbot('openai')
    except ImportError:
        print("Install OpenAI: pip install openai")
    """)
    
    print("\n4. Handle chat errors:")
    print("""
    try:
        response = chatbot.send_message(message)
    except Exception as e:
        print(f"Chat error: {e}")
        response = "Sorry, I encountered an error"
    """)
    
    print("\n✓ Example 6 complete\n")


def main():
    """Run all examples."""
    print("\n" + "="*70)
    print("WeSi Chatbot Examples")
    print("="*70)
    
    examples = [
        ("Basic Usage", example_1_basic_usage),
        ("Custom Chatbot", example_2_custom_chatbot),
        ("Analysis + Chat", example_3_programmatic_analysis_and_chat),
        ("Multi-Provider", example_4_multi_provider),
        ("Context Management", example_5_context_management),
        ("Error Handling", example_6_error_handling),
    ]
    
    for name, example_func in examples:
        try:
            example_func()
        except Exception as e:
            print(f"\n✗ {name} failed: {e}\n")
    
    print("="*70)
    print("All Examples Complete!")
    print("="*70)
    print("\nTo use with real AI providers:")
    print("1. Install provider: pip install openai")
    print("2. Set API key: export OPENAI_API_KEY='your-key'")
    print("3. Run: python wesi.py https://example.com --chat")
    print("="*70 + "\n")


if __name__ == '__main__':
    main()
