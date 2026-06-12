#!/usr/bin/env python3
"""
Verification script to ensure WeSi is properly installed and functional.
"""

import sys

def verify_installation():
    """Verify all components are working."""
    print("="*60)
    print("WeSi Installation Verification")
    print("="*60)
    
    checks_passed = 0
    checks_total = 0
    
    # Check 1: Python version
    checks_total += 1
    print("\n1. Checking Python version...", end=" ")
    if sys.version_info >= (3, 7):
        print("✓ PASSED")
        print(f"   Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")
        checks_passed += 1
    else:
        print("✗ FAILED")
        print("   Python 3.7+ required")
    
    # Check 2: Import main module
    checks_total += 1
    print("\n2. Checking website_analyzer module...", end=" ")
    try:
        from website_analyzer import WebsiteAnalyzer
        print("✓ PASSED")
        checks_passed += 1
    except ImportError as e:
        print("✗ FAILED")
        print(f"   Error: {e}")
    
    # Check 3: Dependencies
    checks_total += 1
    print("\n3. Checking dependencies...", end=" ")
    try:
        import requests
        import bs4
        import lxml
        print("✓ PASSED")
        print(f"   requests: {requests.__version__}")
        print(f"   beautifulsoup4: {bs4.__version__}")
        checks_passed += 1
    except ImportError as e:
        print("✗ FAILED")
        print(f"   Error: {e}")
        print("   Run: pip install -r requirements.txt")
    
    # Check 4: Create analyzer instance
    checks_total += 1
    print("\n4. Testing WebsiteAnalyzer initialization...", end=" ")
    try:
        from website_analyzer import WebsiteAnalyzer
        analyzer = WebsiteAnalyzer('https://test.com')
        print("✓ PASSED")
        checks_passed += 1
    except Exception as e:
        print("✗ FAILED")
        print(f"   Error: {e}")
    
    # Check 5: Test HTML parsing
    checks_total += 1
    print("\n5. Testing HTML parsing...", end=" ")
    try:
        from website_analyzer import WebsiteAnalyzer
        from bs4 import BeautifulSoup
        analyzer = WebsiteAnalyzer('https://test.com')
        soup = BeautifulSoup("<html><body><h1>Test</h1></body></html>", 'html.parser')
        result = analyzer.analyze_heading_hierarchy(soup)
        if result['counts']['h1'] == 1:
            print("✓ PASSED")
            checks_passed += 1
        else:
            print("✗ FAILED - Incorrect parsing")
    except Exception as e:
        print("✗ FAILED")
        print(f"   Error: {e}")
    
    # Summary
    print("\n" + "="*60)
    print(f"VERIFICATION SUMMARY: {checks_passed}/{checks_total} checks passed")
    print("="*60)
    
    if checks_passed == checks_total:
        print("\n✓ All checks passed! WeSi is ready to use.")
        print("\nQuick start:")
        print("  python website_analyzer.py https://yourwebsite.com")
        return 0
    else:
        print("\n✗ Some checks failed. Please review the errors above.")
        return 1

if __name__ == '__main__':
    sys.exit(verify_installation())
