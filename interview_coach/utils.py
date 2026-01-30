"""Utility functions for Interview Coach."""

import re
from typing import Optional


def detect_stop_command(message: str) -> bool:
    """Detect if message contains a stop command.
    
    Args:
        message: User message to check
    
    Returns:
        True if stop command detected
    """
    stop_patterns = [
        r'\bстоп\b',
        r'\bstop\b',
        r'\bхватит\b',
        r'\bзавершить\b',
        r'\bзакончить\b',
        r'\bстоп\s*игра\b',
        r'\bстоп\s*интервью\b',
        r'\bдавай\s*фидбэк\b',
        r'\bдавай\s*feedback\b',
    ]
    
    message_lower = message.lower()
    
    for pattern in stop_patterns:
        if re.search(pattern, message_lower):
            return True
    
    return False


def detect_candidate_question(message: str) -> Optional[str]:
    """Detect if the message is a question from the candidate.
    
    Args:
        message: User message to check
    
    Returns:
        The question if detected, None otherwise
    """
    # Question markers
    question_indicators = [
        '?',
        'какие',
        'какой',
        'какая',
        'как',
        'почему',
        'зачем',
        'что',
        'где',
        'когда',
        'сколько',
        'можно ли',
        'будет ли',
        'есть ли',
        'а вы',
        'а у вас',
        'слушайте',
    ]
    
    message_lower = message.lower()
    
    # Check for question mark
    if '?' in message:
        return message
    
    # Check for question words at the start
    for indicator in question_indicators:
        if message_lower.startswith(indicator):
            return message
    
    return None


def detect_off_topic(message: str) -> bool:
    """Detect if message is off-topic.
    
    Args:
        message: User message to check
    
    Returns:
        True if off-topic detected
    """
    off_topic_patterns = [
        r'\bпогод[аеуы]\b',
        r'\bкофе\b',
        r'\bобед\b',
        r'\bвыходны[еых]\b',
        r'\bотпуск\b',
        r'\bанекдот\b',
        r'\bшутк[аиу]\b',
        r'\bспорт\b',
        r'\bфутбол\b',
        r'\bкино\b',
        r'\bфильм\b',
        r'\bсериал\b',
        r'\bмузык[аеуи]\b',
    ]
    
    message_lower = message.lower()
    
    for pattern in off_topic_patterns:
        if re.search(pattern, message_lower):
            return True
    
    return False


def clean_response(response: str) -> str:
    """Clean up LLM response for display.
    
    Args:
        response: Raw LLM response
    
    Returns:
        Cleaned response
    """
    # Remove common prefixes
    prefixes_to_remove = [
        "Интервьюер:",
        "Interviewer:",
        "AI:",
        "Response:",
    ]
    
    cleaned = response.strip()
    
    for prefix in prefixes_to_remove:
        if cleaned.startswith(prefix):
            cleaned = cleaned[len(prefix):].strip()
    
    return cleaned


def truncate_text(text: str, max_length: int = 500, suffix: str = "...") -> str:
    """Truncate text to maximum length.
    
    Args:
        text: Text to truncate
        max_length: Maximum length
        suffix: Suffix to add if truncated
    
    Returns:
        Truncated text
    """
    if len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)] + suffix


def format_score_bar(score: float, width: int = 10) -> str:
    """Create a visual score bar.
    
    Args:
        score: Score 0.0-1.0
        width: Bar width in characters
    
    Returns:
        Visual bar string
    """
    filled = int(score * width)
    empty = width - filled
    return f"[{'█' * filled}{'░' * empty}] {score:.0%}"


def estimate_grade_from_scores(
    avg_score: float,
    target_grade: str,
    hallucination_count: int = 0
) -> tuple[str, str, int]:
    """Estimate candidate grade from interview scores.
    
    Args:
        avg_score: Average answer score (0-1)
        target_grade: Target grade they applied for
        hallucination_count: Number of hallucinations detected
    
    Returns:
        Tuple of (assessed_grade, recommendation, confidence)
    """
    # Penalty for hallucinations
    adjusted_score = avg_score - (hallucination_count * 0.1)
    adjusted_score = max(0, adjusted_score)
    
    # Determine assessed grade
    if adjusted_score >= 0.8:
        if target_grade == "Junior":
            assessed = "Middle"  # They exceeded expectations
        else:
            assessed = target_grade
        recommendation = "Strong Hire"
        confidence = int(min(95, adjusted_score * 100))
    elif adjusted_score >= 0.6:
        assessed = target_grade
        recommendation = "Hire"
        confidence = int(adjusted_score * 100)
    elif adjusted_score >= 0.4:
        if target_grade == "Senior":
            assessed = "Middle"
        elif target_grade == "Middle":
            assessed = "Junior"
        else:
            assessed = "Junior"
        recommendation = "Hire" if adjusted_score >= 0.5 else "No Hire"
        confidence = int(adjusted_score * 100)
    else:
        assessed = "Junior"
        recommendation = "No Hire"
        confidence = max(30, int(adjusted_score * 100))
    
    return assessed, recommendation, confidence
