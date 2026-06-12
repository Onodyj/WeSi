"""
Plain text report generator for email/CLI consumption.
"""
from typing import Dict, List


class TextReportGenerator:
    """Generates concise plain-text reports optimized for email/CLI."""
    
    def generate(self, analysis_data: Dict, include_pages: bool = False) -> str:
        """
        Generate plain text report from analysis data.
        
        Args:
            analysis_data: Complete analysis data dictionary
            include_pages: Whether to include individual page summaries
            
        Returns:
            Plain text string
        """
        metadata = analysis_data.get('metadata', {})
        summary = analysis_data.get('summary', {})
        insights = analysis_data.get('insights', {})
        pages = analysis_data.get('pages', [])
        
        lines = [
            "="*70,
            "WEBSITE ANALYSIS REPORT",
            "="*70,
            "",
            f"Domain: {metadata.get('domain', 'Unknown')}",
            f"URL: {metadata.get('base_url', '')}",
            f"Analysis Date: {metadata.get('analysis_date', 'Unknown')}",
            f"Pages Crawled: {metadata.get('pages_crawled', 0)}",
            "",
            "="*70,
            "EXECUTIVE SUMMARY",
            "="*70,
            "",
            self._generate_executive_summary(summary, insights),
            "",
            "="*70,
            "KEY STATISTICS",
            "="*70,
            "",
            self._generate_statistics(summary),
            "",
            "="*70,
            "DETAILED INSIGHTS",
            "="*70,
            "",
            self._generate_insights(insights),
        ]
        
        if include_pages and pages:
            lines.extend([
                "",
                "="*70,
                "PAGE SUMMARIES",
                "="*70,
                "",
                self._generate_page_summaries(pages)
            ])
        
        lines.append("")
        lines.append("="*70)
        lines.append("END OF REPORT")
        lines.append("="*70)
        
        return '\n'.join(lines)
    
    def _generate_executive_summary(self, summary: Dict, insights: Dict) -> str:
        """Generate executive summary."""
        lines = []
        
        critical = insights.get('critical', [])
        warnings = insights.get('warnings', [])
        recommendations = insights.get('recommendations', [])
        positive = insights.get('positive', [])
        
        # Overview
        lines.append("SITE HEALTH OVERVIEW")
        lines.append("-" * 70)
        lines.append(f"Total Issues Found: {len(critical) + len(warnings)}")
        lines.append(f"  - Critical: {len(critical)}")
        lines.append(f"  - Warnings: {len(warnings)}")
        lines.append(f"  - Recommendations: {len(recommendations)}")
        lines.append(f"  - Positive Findings: {len(positive)}")
        lines.append("")
        
        # Top priority items
        lines.append("TOP PRIORITY ACTION ITEMS")
        lines.append("-" * 70)
        
        priority_count = 0
        
        # Add critical issues
        for item in critical[:3]:
            priority_count += 1
            lines.append(f"{priority_count}. [CRITICAL] {item}")
        
        # Add warnings
        for item in warnings[:2]:
            priority_count += 1
            lines.append(f"{priority_count}. [WARNING] {item}")
        
        # Add recommendations
        for item in recommendations[:2]:
            priority_count += 1
            lines.append(f"{priority_count}. [RECOMMENDATION] {item}")
        
        if priority_count == 0:
            lines.append("✓ No critical issues found - site is in good health!")
        
        return '\n'.join(lines)
    
    def _generate_statistics(self, summary: Dict) -> str:
        """Generate statistics section."""
        stats = [
            f"Pages Analyzed:         {summary.get('total_pages_analyzed', 0)}",
            f"Total Images:           {summary.get('total_images', 0)}",
            f"Images w/o Alt Text:    {summary.get('images_without_alt', 0)}",
            f"Internal Links:         {summary.get('total_internal_links', 0)}",
            f"External Links:         {summary.get('total_external_links', 0)}",
            f"Broken Links Found:     {summary.get('broken_links_found', 0)}",
            f"Average Word Count:     {summary.get('avg_word_count', 0)}",
        ]
        
        return '\n'.join(stats)
    
    def _generate_insights(self, insights: Dict) -> str:
        """Generate insights section."""
        lines = []
        
        # Critical issues
        critical = insights.get('critical', [])
        if critical:
            lines.append("🔴 CRITICAL ISSUES")
            lines.append("-" * 70)
            for idx, item in enumerate(critical, 1):
                lines.append(f"{idx}. {item}")
            lines.append("")
        
        # Warnings
        warnings = insights.get('warnings', [])
        if warnings:
            lines.append("⚠️  WARNINGS")
            lines.append("-" * 70)
            for idx, item in enumerate(warnings, 1):
                lines.append(f"{idx}. {item}")
            lines.append("")
        
        # Recommendations
        recommendations = insights.get('recommendations', [])
        if recommendations:
            lines.append("💡 RECOMMENDATIONS")
            lines.append("-" * 70)
            for idx, item in enumerate(recommendations, 1):
                lines.append(f"{idx}. {item}")
            lines.append("")
        
        # Positive findings
        positive = insights.get('positive', [])
        if positive:
            lines.append("✅ POSITIVE FINDINGS")
            lines.append("-" * 70)
            for idx, item in enumerate(positive, 1):
                lines.append(f"{idx}. {item}")
            lines.append("")
        
        if not any([critical, warnings, recommendations, positive]):
            lines.append("No insights generated.")
        
        return '\n'.join(lines)
    
    def _generate_page_summaries(self, pages: List[Dict]) -> str:
        """Generate brief summaries for each page."""
        lines = []
        
        for idx, page in enumerate(pages, 1):
            url = page.get('url', 'Unknown')
            status_code = page.get('status_code', 0)
            seo = page.get('seo', {})
            suggestions = page.get('suggestions', [])
            
            # Truncate URL if too long
            display_url = url if len(url) <= 65 else url[:62] + '...'
            
            lines.append(f"Page {idx}: {display_url}")
            lines.append(f"  Status: {status_code}")
            lines.append(f"  Title: {seo.get('title', 'Not set')[:60]}")
            lines.append(f"  Word Count: {seo.get('word_count', 0)}")
            
            # Count issues by priority
            critical_count = sum(1 for s in suggestions if s.get('priority') == 'critical')
            high_count = sum(1 for s in suggestions if s.get('priority') == 'high')
            
            if critical_count > 0 or high_count > 0:
                lines.append(f"  Issues: {critical_count} critical, {high_count} high priority")
            else:
                lines.append("  Issues: None")
            
            lines.append("")
        
        return '\n'.join(lines)
    
    def generate_email_summary(self, analysis_data: Dict) -> str:
        """
        Generate a brief email-friendly summary.
        
        Args:
            analysis_data: Complete analysis data dictionary
            
        Returns:
            Email-friendly plain text summary
        """
        metadata = analysis_data.get('metadata', {})
        summary = analysis_data.get('summary', {})
        insights = analysis_data.get('insights', {})
        
        critical = insights.get('critical', [])
        warnings = insights.get('warnings', [])
        
        lines = [
            f"Website Analysis Complete: {metadata.get('domain', 'Unknown')}",
            "",
            "Quick Summary:",
            f"- {summary.get('total_pages_analyzed', 0)} pages analyzed",
            f"- {len(critical)} critical issues",
            f"- {len(warnings)} warnings",
            "",
        ]
        
        if critical:
            lines.append("Top Critical Issues:")
            for item in critical[:3]:
                lines.append(f"  • {item}")
            lines.append("")
        
        if warnings:
            lines.append("Top Warnings:")
            for item in warnings[:3]:
                lines.append(f"  • {item}")
            lines.append("")
        
        lines.append("View the full report for detailed analysis and recommendations.")
        
        return '\n'.join(lines)
