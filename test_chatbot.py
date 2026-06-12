#!/usr/bin/env python3
"""
Test script to verify chatbot integration without requiring API keys.
Tests the base ChatbotInterface and extensibility.
"""

import json
import sys
from chatbot import ChatbotInterface, create_chatbot


class MockChatbot(ChatbotInterface):
    """Mock chatbot for testing without API keys."""
    
    def send_message(self, message: str) -> str:
        """Send message to mock chatbot and get response."""
        # Add to history
        self.conversation_history.append({"role": "user", "content": message})
        
        # Generate mock responses based on keywords
        message_lower = message.lower()
        
        if not self.analysis_data:
            response = "I don't have any analysis data loaded. Please provide an analysis report."
        elif "summary" in message_lower or "overview" in message_lower:
            summary = self.analysis_data.get('summary', {})
            response = f"""Here's a summary of the analysis:
- Pages analyzed: {summary.get('total_pages_analyzed', 0)}
- Total images: {summary.get('total_images', 0)}
- Images without alt text: {summary.get('images_without_alt', 0)}
- Internal links: {summary.get('total_internal_links', 0)}
- External links: {summary.get('total_external_links', 0)}
- Broken links: {summary.get('broken_links_found', 0)}
- Average word count: {summary.get('avg_word_count', 0)}
"""
        elif "critical" in message_lower or "issue" in message_lower:
            insights = self.analysis_data.get('insights', {})
            critical = insights.get('critical', [])
            if critical:
                response = "Critical issues found:\n" + "\n".join(f"- {issue}" for issue in critical)
            else:
                response = "No critical issues found! 🎉"
        elif "seo" in message_lower:
            response = "For SEO optimization, focus on: adding title tags, meta descriptions, and ensuring proper heading hierarchy."
        elif "help" in message_lower:
            response = """You can ask me about:
- Summary of the analysis
- Critical issues
- SEO recommendations
- Images and alt text
- Links and broken links
- Content quality"""
        else:
            response = f"I received your question: '{message}'. In a real chatbot, I would analyze this against your website data and provide detailed insights."
        
        # Add to history
        self.conversation_history.append({"role": "assistant", "content": response})
        
        # Keep history manageable
        if len(self.conversation_history) > 20:
            self.conversation_history = self.conversation_history[-20:]
        
        return response


def test_chatbot_interface():
    """Test the chatbot interface."""
    print("Testing ChatbotInterface...")
    
    # Load test analysis
    try:
        with open('test_analysis.json', 'r') as f:
            analysis_data = json.load(f)
        print("✓ Loaded test analysis data")
    except FileNotFoundError:
        print("✗ test_analysis.json not found. Run analysis first.")
        return False
    
    # Create mock chatbot
    chatbot = MockChatbot(analysis_data=analysis_data)
    print("✓ Created mock chatbot instance")
    
    # Test system prompt generation
    system_prompt = chatbot.get_system_prompt()
    assert "website" in system_prompt.lower()
    assert "analysis" in system_prompt.lower()
    print("✓ System prompt generated correctly")
    
    # Test sending messages
    response1 = chatbot.send_message("Give me a summary")
    assert "Pages analyzed" in response1
    print("✓ Summary response generated")
    
    response2 = chatbot.send_message("What are the critical issues?")
    assert "critical" in response2.lower() or "issues" in response2.lower()
    print("✓ Critical issues response generated")
    
    # Test conversation history
    assert len(chatbot.conversation_history) == 4  # 2 exchanges
    print("✓ Conversation history maintained")
    
    print("\n✅ All ChatbotInterface tests passed!\n")
    return True


def test_extensibility():
    """Test that custom chatbots can be created."""
    print("Testing extensibility...")
    
    class CustomChatbot(ChatbotInterface):
        def send_message(self, message: str) -> str:
            return f"Custom response to: {message}"
    
    custom = CustomChatbot()
    response = custom.send_message("test")
    assert response == "Custom response to: test"
    print("✓ Custom chatbot can be created")
    
    print("\n✅ Extensibility tests passed!\n")
    return True


def test_factory():
    """Test the chatbot factory function."""
    print("Testing factory function...")
    
    # Test that factory requires proper provider
    try:
        chatbot = create_chatbot("invalid_provider")
        print("✗ Factory should reject invalid provider")
        return False
    except ValueError as e:
        print(f"✓ Factory correctly rejects invalid provider: {e}")
    
    print("\n✅ Factory tests passed!\n")
    return True


def test_integration():
    """Test integration with wesi.py."""
    print("Testing integration with wesi.py...")
    
    # Check that chatbot can be imported from wesi
    try:
        # Try importing the chatbot module
        import chatbot as cb
        print("✓ chatbot module can be imported")
        
        # Check key classes exist
        assert hasattr(cb, 'ChatbotInterface')
        assert hasattr(cb, 'OpenAIChatbot')
        assert hasattr(cb, 'AnthropicChatbot')
        assert hasattr(cb, 'GoogleChatbot')
        assert hasattr(cb, 'create_chatbot')
        assert hasattr(cb, 'interactive_chat_session')
        print("✓ All required classes and functions exist")
        
    except ImportError as e:
        print(f"✗ Failed to import chatbot: {e}")
        return False
    
    print("\n✅ Integration tests passed!\n")
    return True


def main():
    """Run all tests."""
    print("="*70)
    print("WeSi Chatbot Integration Tests")
    print("="*70 + "\n")
    
    tests = [
        test_chatbot_interface,
        test_extensibility,
        test_factory,
        test_integration
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"✗ Test failed with exception: {e}")
            results.append(False)
    
    print("="*70)
    print("TEST SUMMARY")
    print("="*70)
    passed = sum(results)
    total = len(results)
    print(f"Passed: {passed}/{total}")
    
    if passed == total:
        print("\n🎉 All tests passed!")
        return 0
    else:
        print("\n⚠️  Some tests failed")
        return 1


if __name__ == '__main__':
    sys.exit(main())
