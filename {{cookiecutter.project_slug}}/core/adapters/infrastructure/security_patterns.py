# core/adapters/infrastructure/security_patterns.py
"""
Enhanced security pattern matching and threat detection.

Comprehensive patterns for detecting:
- SQL injection variants
- XSS attribute attacks
- Command injection
- Path traversal
"""
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Set, Pattern
import re
from enum import Enum
from abc import ABC, abstractmethod


class ThreatCategory(str, Enum):
    """Categories of security threats"""
    INJECTION = "injection"
    XSS = "xss"
    PATH_TRAVERSAL = "path_traversal"
    COMMAND_INJECTION = "command_injection"
    HEADER_INJECTION = "header_injection"
    SCANNER = "scanner"
    SPAM = "spam"
    DOS = "dos"


class ThreatSeverity(str, Enum):
    """Severity levels for detected threats"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class SecurityPattern:
    """Individual security pattern definition with enhanced matching"""
    name: str
    category: ThreatCategory
    severity: ThreatSeverity
    description: str
    patterns: List[str]
    compiled_patterns: List[Pattern] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    false_positives: Set[str] = field(default_factory=set)
    weight: float = 1.0

    def __post_init__(self):
        """Compile regex patterns"""
        self.compiled_patterns = []
        for pattern in self.patterns:
            try:
                compiled = re.compile(pattern, re.IGNORECASE | re.MULTILINE)
                self.compiled_patterns.append(compiled)
            except re.error as e:
                raise ValueError(f"Invalid regex pattern '{pattern}': {str(e)}")


@dataclass
class SecurityMatch:
    """Details of a pattern match with enhanced metadata"""
    pattern: SecurityPattern
    matched_value: str
    match_location: str
    confidence: float
    context: Dict[str, Any] = field(default_factory=dict)
    match_start: int = 0
    match_end: int = 0


class DetectionStrategy(ABC):
    """Base class for detection strategies"""

    @abstractmethod
    def analyze(self, content: str, pattern: SecurityPattern) -> List[SecurityMatch]:
        """
        Analyze content for security threats

        :param content: Content to analyze
        :param pattern: Pattern to match against
        :return: List of matches found
        """
        pass


class RegexStrategy(DetectionStrategy):
    """Enhanced regex-based pattern matching"""

    def analyze(self, content: str, pattern: SecurityPattern) -> List[SecurityMatch]:
        """Analyze content for matches"""
        if not content:
            return []

        matches = []
        for compiled in pattern.compiled_patterns:
            for match in compiled.finditer(content):
                confidence = self._calculate_confidence(match, pattern, content)
                if confidence > 0.0:
                    matches.append(SecurityMatch(
                        pattern=pattern,
                        matched_value=match.group(),
                        match_location="content",
                        confidence=confidence,
                        match_start=match.start(),
                        match_end=match.end()
                    ))
        return matches

    def _calculate_confidence(self, match: re.Match, pattern: SecurityPattern, content: str) -> float:
        """
        Calculate confidence with detailed context analysis

        :param match: Regex match object
        :param pattern: The SecurityPattern that matched
        :param content: The entire content being analyzed
        :return: Confidence score between 0 and 1
        """
        # Context and location
        value = match.group()
        total_length = len(content)
        start = match.start()

        # Base confidence factors
        base_factors = {}

        # Category-specific detection
        if pattern.category == ThreatCategory.INJECTION:
            base_factors = self._sql_injection_confidence(value, content)
        elif pattern.category == ThreatCategory.XSS:
            base_factors = self._xss_confidence(value, content)
        elif pattern.category == ThreatCategory.PATH_TRAVERSAL:
            base_factors = self._path_traversal_confidence(value, content)
        elif pattern.category == ThreatCategory.COMMAND_INJECTION:
            base_factors = self._command_injection_confidence(value, content)

        # Combine factors
        length_factor = min(len(value) / 20, 0.3)
        position_factor = 1.0 - (start / max(total_length, 1))
        weight_factor = min(pattern.weight * 0.2, 0.2)

        # Aggregate confidence
        confidence_factors = list(base_factors.values()) + [
            length_factor,
            position_factor,
            weight_factor
        ]

        confidence = min(sum(confidence_factors), 1.0)

        # Additional filtering for context
        if pattern.category == ThreatCategory.PATH_TRAVERSAL:
            # Stricter filtering for path traversal to avoid false positives
            if any(legit in content.lower() for legit in ['index.html', 'www', 'html', 'docs']):
                confidence = min(confidence, 0.3)

        return max(confidence, 0.0)

    def _sql_injection_confidence(self, value: str, content: str) -> Dict[str, float]:
        """Confidence calculation for SQL injection"""
        # Sophisticated SQL injection indicators
        indicators = {
            'quote_presence': 0.2 if any(c in value for c in "'\"") else 0,
            'or_and_presence': 0.3 if re.search(r'\b(OR|AND)\b', value, re.IGNORECASE) else 0,
            'equality_pattern': 0.2 if re.search(r'\w+\s*=\s*\w+', value) else 0,
            'comment_presence': 0.1 if any(c in value for c in '#-') else 0,
            'numeric_comparison': 0.2 if re.search(r'\d+\s*=\s*\d+', value) else 0
        }
        return indicators

    def _xss_confidence(self, value: str, content: str) -> Dict[str, float]:
        """Confidence calculation for XSS"""
        # XSS-specific indicators
        indicators = {
            'script_tag': 0.3 if '<script' in value.lower() else 0,
            'event_handler': 0.3 if re.search(r'on\w+\s*=', value, re.IGNORECASE) else 0,
            'javascript_protocol': 0.2 if 'javascript:' in value.lower() else 0,
            'special_chars': 0.2 if any(c in value for c in '<>"\'`') else 0
        }
        return indicators

    def _path_traversal_confidence(self, value: str, content: str) -> Dict[str, float]:
        """Confidence calculation for path traversal"""
        # Path traversal indicators
        indicators = {
            'dot_dot_slash': 0.3 if '../' in value or '..' in value else 0,
            'url_encoded': 0.2 if '%2e' in value.lower() else 0,
            'system_paths': 0.3 if any(
                path in value for path in ['/var/', '/bin/', 'shadow']) else 0,
            'windows_paths': 0.2 if re.search(r'(\.\.\\|win\.ini|system32)', value, re.IGNORECASE) else 0
        }
        return indicators

    def _command_injection_confidence(self, value: str, content: str) -> Dict[str, float]:
        """Confidence calculation for command injection"""
        # Command injection indicators
        indicators = {
            'shell_commands': 0.3 if any(cmd in value.lower() for cmd in ['ls', 'rm', 'whoami', 'net']) else 0,
            'command_substitution': 0.2 if any(sub in value for sub in ['`', '$(', '$']) else 0,
            'system_cmd_paths': 0.2 if re.search(r'(/bin/|cmd\.exe|powershell)', value, re.IGNORECASE) else 0
        }
        return indicators


class SecurityPatternMatcher:
    """Security pattern matcher with testable patterns"""

    # Comprehensive SQL Injection Patterns
    SQL_INJECTION_PATTERNS = [
        r"(?i)['\"]\s*(?:OR|AND)\s*(?:[\w\d]+\s*=\s*[\w\d]+|\d+\s*=\s*\d+)",
        r"(?i)(\d+\s*(?:OR|AND)\s*\d+\s*=\s*\d+)",
        r"(?i)(UNION\s+(?:ALL\s+)?SELECT)",
        r"(?i)('.*?OR.*?=.*?')",
        r"(?i)(1\s*=\s*1)",
    ]

    # XSS Patterns - More comprehensive
    XSS_PATTERNS = [
        r"<script[^>]*>[\s\S]*?</script>",
        r"(?i)javascript:[^'\"]*",
        r"(?i)on(?:load|click|mouse|error|focus|mouseover)\s*=",
        r"(?i)(?:src|href)\s*=\s*['\"]?(?:javascript|data):",
    ]

    # Command Injection Patterns
    COMMAND_INJECTION_PATTERNS = [
        r"/bin/(?:bash|sh|zsh)",  # Shell references
    ]

    def __init__(self):
        """Initialize patterns and strategies"""
        self.patterns: List[SecurityPattern] = []
        self._load_patterns()
        self.strategies = [RegexStrategy()]

    def _load_patterns(self):
        """Load patterns from class variables"""
        self.patterns = [
            SecurityPattern(
                name="SQL Injection",
                category=ThreatCategory.INJECTION,
                severity=ThreatSeverity.HIGH,
                description="SQL injection attempt",
                patterns=self.SQL_INJECTION_PATTERNS,
                weight=1.2
            ),
            SecurityPattern(
                name="Cross-Site Scripting",
                category=ThreatCategory.XSS,
                severity=ThreatSeverity.HIGH,
                description="XSS attempt",
                patterns=self.XSS_PATTERNS,
                weight=1.1
            ),
            SecurityPattern(
                name="Command Injection",
                category=ThreatCategory.COMMAND_INJECTION,
                severity=ThreatSeverity.CRITICAL,
                description="Command injection attempt",
                patterns=self.COMMAND_INJECTION_PATTERNS,
                weight=1.3
            ),
        ]

    @classmethod
    def test_patterns(cls) -> Dict[str, List[str]]:
        """
        Get all regex patterns for testing.

        :return: Dict of pattern lists by category
        """
        return {
            'sql_injection': cls.SQL_INJECTION_PATTERNS,
            'xss': cls.XSS_PATTERNS,
            'command_injection': cls.COMMAND_INJECTION_PATTERNS
        }

    def scan(self, content: str, location: str) -> List[SecurityMatch]:
        """Scan with improved location tracking"""
        matches = []

        for pattern in self.patterns:
            # Add location to pattern metadata
            pattern.metadata['match_location'] = location

            for strategy in self.strategies:
                new_matches = strategy.analyze(content, pattern)
                for match in new_matches:
                    match.match_location = location
                matches.extend(new_matches)

        return self._filter_matches(matches)

    def _filter_matches(self, matches: List[SecurityMatch]) -> List[SecurityMatch]:
        """Filter matches by confidence and avoid duplicates"""
        # Sophisticated filtering
        filtered_matches = []
        category_confidences = {}

        for match in matches:
            # More nuanced confidence threshold
            if match.confidence > 0.3 and match.matched_value not in match.pattern.false_positives:
                # Track highest confidence for each category
                cat_key = match.pattern.category
                current_max = category_confidences.get(cat_key, 0)

                # Prioritize higher confidence matches per category
                if match.confidence > current_max:
                    # Remove previous lower confidence matches for the same category
                    filtered_matches = [
                        m for m in filtered_matches
                        if m.pattern.category != cat_key
                    ]
                    filtered_matches.append(match)
                    category_confidences[cat_key] = match.confidence
                elif match.confidence == current_max:
                    # If equal confidence, add to list
                    filtered_matches.append(match)

        return filtered_matches