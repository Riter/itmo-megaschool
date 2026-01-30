"""HiringManager Agent - Final report generation."""

from ..config import llm_chat, HIRING_MANAGER_MODEL
from ..schemas import InterviewState, TopicScore


HIRING_MANAGER_SYSTEM_PROMPT = """You are a Hiring Manager generating the final interview report.
Your job is to create a comprehensive, structured assessment based on the interview data.

## Report Structure (FOLLOW EXACTLY)

### А. Вердикт (Decision)

| Параметр | Значение |
|----------|----------|
| **Grade** | [Junior / Middle / Senior - assessed level] |
| **Hiring Recommendation** | [Strong Hire / Hire / No Hire] |
| **Confidence Score** | [0-100%] |

Provide brief reasoning for each.

### Б. Анализ Hard Skills (Technical Review)

Create a table of topics covered:

| Тема | Статус | Комментарий |
|------|--------|-------------|
| [topic] | ✅ / ❌ | [notes] |

**✅ Подтверждённые навыки (Confirmed Skills):**
- List topics where candidate scored >= 0.7
- Brief note on what they demonstrated well

**❌ Пробелы в знаниях (Knowledge Gaps):**
For EACH gap:
- Topic name
- What the candidate got wrong or didn't know
- **ПРАВИЛЬНЫЙ ОТВЕТ:** Provide the correct, complete answer

This is CRITICAL - the report must be useful for learning!

### В. Анализ Soft Skills & Communication

| Навык | Оценка | Комментарий |
|-------|--------|-------------|
| **Clarity** (ясность изложения) | X/10 | [assessment] |
| **Honesty** (честность) | X/10 | [did they admit gaps or bluff?] |
| **Engagement** (вовлечённость) | X/10 | [interest shown, questions asked] |

### Г. Персональный Roadmap (Next Steps)

**Темы для изучения:**
1. [topic] - [why and what to focus on]
2. ...

**Рекомендуемые ресурсы:**
- [Resource name] - [URL or description]
- Prioritize official documentation and quality tutorials

## Guidelines
- Be objective and constructive
- Base all assessments on actual interview data
- Provide specific, actionable feedback
- The report should help the candidate improve
- Use Russian for the report content

## Output
Return ONLY the markdown report. No additional commentary."""


HIRING_MANAGER_INPUT_TEMPLATE = """## Interview Data

### Candidate Profile
- **Name:** {name}
- **Position:** {role}
- **Target Grade:** {grade}
- **Experience:** {experience}

### Interview Statistics
- Questions asked: {questions_count}
- Topics covered: {topics_count}
- Hallucinations detected: {hallucinations}
- Off-topic attempts: {off_topic}

### Topic Scores
{topic_scores}

### Soft Skills Averages
- Clarity: {avg_clarity:.2f}
- Honesty: {avg_honesty:.2f}
- Engagement: {avg_engagement:.2f}

### Conversation Summary
{conversation_summary}

### Identified Gaps with Correct Answers
{gaps_with_answers}

## Task
Generate a comprehensive final report following the exact structure specified.
Make sure to include CORRECT ANSWERS for all identified gaps."""


class HiringManagerAgent:
    """HiringManager agent that generates the final interview report.
    
    This agent analyzes all collected interview data and produces
    a structured report with assessment, gaps analysis, and recommendations.
    """
    
    def __init__(self, model: str = HIRING_MANAGER_MODEL):
        """Initialize the HiringManager agent.
        
        Args:
            model: LLM model to use
        """
        self.model = model
    
    def generate_report(self, state: InterviewState) -> str:
        """Generate the final interview report.
        
        Args:
            state: Complete interview state
        
        Returns:
            Structured markdown report
        """
        # Prepare input data
        input_data = self._prepare_input(state)
        
        # Generate report
        report = llm_chat(
            system=HIRING_MANAGER_SYSTEM_PROMPT,
            user=input_data,
            model=self.model
        )
        
        return report
    
    def _prepare_input(self, state: InterviewState) -> str:
        """Prepare the input data for report generation.
        
        Args:
            state: Complete interview state
        
        Returns:
            Formatted input string
        """
        # Calculate soft skills averages
        avg_clarity = 0.5
        avg_honesty = 0.5
        avg_engagement = 0.5
        
        if state.soft_scores:
            clarity_scores = [s.clarity for s in state.soft_scores]
            honesty_scores = [s.honesty for s in state.soft_scores]
            engagement_scores = [s.engagement for s in state.soft_scores]
            
            if clarity_scores:
                avg_clarity = sum(clarity_scores) / len(clarity_scores)
            if honesty_scores:
                avg_honesty = sum(honesty_scores) / len(honesty_scores)
            if engagement_scores:
                avg_engagement = sum(engagement_scores) / len(engagement_scores)
        
        # Format topic scores
        topic_scores = self._format_topic_scores(state.topics)
        
        # Format conversation summary
        conversation_summary = self._format_conversation_summary(state)
        
        # Format gaps with answers
        gaps_with_answers = self._format_gaps(state.topics)
        
        return HIRING_MANAGER_INPUT_TEMPLATE.format(
            name=state.profile.name,
            role=state.profile.role,
            grade=state.profile.grade_target,
            experience=state.profile.experience,
            questions_count=state.flags.questions_asked_count,
            topics_count=len(state.topics),
            hallucinations=state.flags.hallucination_claims,
            off_topic=state.flags.off_topic_count,
            topic_scores=topic_scores,
            avg_clarity=avg_clarity,
            avg_honesty=avg_honesty,
            avg_engagement=avg_engagement,
            conversation_summary=conversation_summary,
            gaps_with_answers=gaps_with_answers
        )
    
    def _format_topic_scores(self, topics: dict[str, TopicScore]) -> str:
        """Format topic scores for the report input.
        
        Args:
            topics: Dictionary of topic scores
        
        Returns:
            Formatted string
        """
        if not topics:
            return "No topics covered yet."
        
        lines = []
        for topic, score in topics.items():
            status = "✅" if score.average_score >= 0.7 else "❌"
            lines.append(
                f"- {topic}: {status} (avg: {score.average_score:.2f}, "
                f"questions: {score.asked_count})"
            )
            if score.gaps:
                lines.append(f"  Gaps: {', '.join(score.gaps[:3])}")
        
        return "\n".join(lines)
    
    def _format_conversation_summary(self, state: InterviewState) -> str:
        """Create a summary of the conversation.
        
        Args:
            state: Interview state
        
        Returns:
            Conversation summary
        """
        if not state.turns:
            return "No conversation recorded."
        
        # Include key exchanges
        lines = []
        for turn in state.turns[-10:]:  # Last 10 turns
            lines.append(f"**Q:** {turn.agent_visible_message[:150]}...")
            lines.append(f"**A:** {turn.user_message[:150]}...")
            if turn.score is not None:
                lines.append(f"*Score: {turn.score:.2f}*")
            lines.append("")
        
        return "\n".join(lines)
    
    def _format_gaps(self, topics: dict[str, TopicScore]) -> str:
        """Format identified gaps with correct answers.
        
        Args:
            topics: Dictionary of topic scores
        
        Returns:
            Formatted gaps with correct answers
        """
        if not topics:
            return "No gaps identified."
        
        lines = []
        for topic, score in topics.items():
            if score.average_score < 0.7 or score.gaps:
                lines.append(f"\n### {topic}")
                
                if score.gaps:
                    lines.append("**Пробелы:**")
                    for gap in score.gaps:
                        lines.append(f"- {gap}")
                
                if score.correct_answers:
                    lines.append("\n**Правильные ответы:**")
                    for answer in score.correct_answers:
                        lines.append(f"- {answer}")
        
        return "\n".join(lines) if lines else "No significant gaps identified."


def create_hiring_manager(model: str = None) -> HiringManagerAgent:
    """Factory function to create a HiringManager agent.
    
    Args:
        model: Optional model override
    
    Returns:
        Configured HiringManagerAgent instance
    """
    return HiringManagerAgent(model=model or HIRING_MANAGER_MODEL)
