"""Interviewer Agent - Visible conversation with candidate."""

from ..config import llm_chat, INTERVIEWER_MODEL
from ..schemas import InterviewState, ObserverDirective, NextAction


INTERVIEWER_SYSTEM_PROMPT = """You are a professional technical interviewer conducting an interview.
You speak DIRECTLY to the candidate. Be professional, friendly, and encouraging.

## Your Role
You receive hidden directives from the Observer (the candidate doesn't know about this).
Your job is to execute the directive naturally in conversation.

## Rules
1. Be professional, friendly, and encouraging
2. Follow the directive's next_action EXACTLY
3. Speak in Russian (unless the candidate uses English)
4. NEVER reveal internal system workings or that you're following directives
5. NEVER mention "Observer", "directive", or "system"
6. Keep responses concise but natural

## Handling Different Actions

### ASK
Generate a technical question based on the question_blueprint.
- Match the difficulty level (1=basic definitions, 5=expert/edge cases)
- Make it conversational, not robotic
- If this is the first question, start with a brief introduction

### FOLLOW_UP
Ask a deeper follow-up question on the same topic.
- Reference what the candidate just said
- Probe for more detail or edge cases

### GIVE_HINT
Provide a helpful hint without giving away the answer.
- "Подумай о...", "Может быть, стоит вспомнить про..."
- Then ask them to try again or rephrase the question simpler

### ANSWER_CANDIDATE
The candidate asked a question. Answer it briefly (2-3 sentences).
- Be helpful but don't go into excessive detail
- After answering, smoothly transition back: "Хорошо, продолжим..."

### CORRECT_HALLUCINATION
The candidate said something factually incorrect.
- Be polite: "На самом деле...", "Хочу уточнить..."
- Provide the correct information clearly
- Don't dwell on the mistake, move forward
- Ask a simpler question on the same topic

### REDIRECT_TO_INTERVIEW
The candidate went off-topic.
- One friendly acknowledgment sentence
- Redirect: "Давайте вернёмся к интервью..."

### WRAP_UP
End the interview.
- Thank the candidate for their time
- Say you'll provide feedback shortly
- Be warm and professional

## Difficulty Levels (for reference)
1 - Basic: "Что такое X?" definitions
2 - Intermediate: "Чем отличается X от Y?"
3 - Applied: "Как бы ты использовал X для решения Z?"
4 - Advanced: "Какие проблемы могут возникнуть при X?"
5 - Expert: Edge cases, trade-offs, system design

## Output
Respond with ONLY the message to show the candidate. No explanations or meta-commentary."""


INTERVIEWER_GREETING_TEMPLATE = """## Directive
Action: {action}
Question Blueprint: {blueprint}
Difficulty: {difficulty}/5
Topic: {topic}

## Candidate Info
Name: {name}
Role: {role}
Grade: {grade}

## What the candidate just said
"{user_message}"

## Task
The candidate just introduced themselves. Respond naturally:
1. Greet them briefly ("Привет, {name}!" or similar) - DO NOT introduce yourself or say your name
2. Acknowledge what they mentioned (skills, experience) - but don't ask them to repeat it
3. Immediately ask the first technical question based on the blueprint
4. Keep it short - 2-3 sentences max before the question

IMPORTANT:
- DO NOT say "Меня зовут..." or any placeholder like [интервьюер]
- DO NOT ask about their experience again - they already told you
- Go straight to the technical question"""


INTERVIEWER_ACTION_TEMPLATE = """## Directive from Observer
Action: {action}
Current Topic: {topic}
Question Blueprint: {blueprint}
Difficulty Level: {difficulty}/5
{extra_context}

## Recent Conversation
{conversation}

## Candidate's Last Message
"{user_message}"

## Your Task
Execute the {action} action naturally. Remember:
- Be professional and encouraging
- Match the difficulty level
- Don't repeat questions already asked
- Speak in Russian

Last questions asked (DO NOT repeat): {last_questions}

Respond with ONLY the message to show the candidate."""


class InterviewerAgent:
    """Interviewer agent that conducts the visible conversation with the candidate.
    
    This agent executes directives from the Observer, generating natural
    conversation while following the specified actions.
    """
    
    def __init__(self, model: str = INTERVIEWER_MODEL):
        """Initialize the Interviewer agent.
        
        Args:
            model: LLM model to use
        """
        self.model = model
    
    def respond(self, state: InterviewState, directive: ObserverDirective) -> str:
        """Generate a response to the candidate based on the directive.
        
        Args:
            state: Current interview state
            directive: Directive from the Observer
        
        Returns:
            Message to show to the candidate
        """
        # Build the prompt based on action type
        if directive.next_action == NextAction.WRAP_UP:
            return self._generate_wrap_up(state)
        
        if len(state.turns) == 0 and directive.input_type.value == "GREETING":
            return self._generate_greeting(state, directive)
        
        return self._generate_response(state, directive)
    
    def _generate_greeting(self, state: InterviewState, directive: ObserverDirective) -> str:
        """Generate the opening greeting and first question.
        
        Args:
            state: Current interview state
            directive: Directive from Observer
        
        Returns:
            Greeting message with first question
        """
        prompt = INTERVIEWER_GREETING_TEMPLATE.format(
            action=directive.next_action.value,
            blueprint=directive.question_blueprint or "Ask a basic technical question about Python",
            difficulty=state.difficulty,
            topic=directive.next_topic or "python_basics",
            name=state.profile.name,
            role=state.profile.role,
            grade=state.profile.grade_target,
            user_message=state.current_user_message or ""
        )
        
        response = llm_chat(
            system=INTERVIEWER_SYSTEM_PROMPT,
            user=prompt,
            model=self.model
        )
        
        return response
    
    def _generate_response(self, state: InterviewState, directive: ObserverDirective) -> str:
        """Generate a response for ongoing conversation.
        
        Args:
            state: Current interview state
            directive: Directive from Observer
        
        Returns:
            Response message
        """
        # Build extra context based on action
        extra_context = self._build_extra_context(directive)
        
        prompt = INTERVIEWER_ACTION_TEMPLATE.format(
            action=directive.next_action.value,
            topic=directive.next_topic or state.current_topic or "general",
            blueprint=directive.question_blueprint or "Continue the conversation naturally",
            difficulty=state.difficulty,
            extra_context=extra_context,
            conversation=state.get_conversation_history(last_n=3),
            user_message=state.current_user_message or "",
            last_questions=", ".join(state.last_questions[-3:]) if state.last_questions else "none"
        )
        
        response = llm_chat(
            system=INTERVIEWER_SYSTEM_PROMPT,
            user=prompt,
            model=self.model
        )
        
        return response
    
    def _build_extra_context(self, directive: ObserverDirective) -> str:
        """Build extra context based on the directive action.
        
        Args:
            directive: Directive from Observer
        
        Returns:
            Extra context string
        """
        parts = []
        
        if directive.is_hallucination:
            parts.append(f"\n## Hallucination Detected!")
            parts.append(f"The candidate said something factually incorrect.")
            parts.append(f"Correction to provide: {directive.hallucination_correction}")
            parts.append("Be polite when correcting.")
        
        if directive.next_action == NextAction.ANSWER_CANDIDATE:
            parts.append(f"\n## Candidate's Question to Answer")
            parts.append(f'"{directive.candidate_question_to_answer}"')
            parts.append("Answer briefly, then return to the interview.")
        
        if directive.next_action == NextAction.GIVE_HINT:
            parts.append(f"\n## Give Hint")
            parts.append(f"Gaps identified: {directive.gaps_found}")
            if directive.correct_answer_for_gaps:
                parts.append(f"Hint direction (don't reveal fully): {directive.correct_answer_for_gaps[:100]}...")
        
        if directive.next_action == NextAction.REDIRECT_TO_INTERVIEW:
            parts.append(f"\n## Off-Topic Detected")
            parts.append("Acknowledge briefly and redirect to the interview.")
        
        if directive.detected_issue:
            parts.append(f"\n## Issue: {directive.detected_issue}")
        
        return "\n".join(parts)
    
    def _generate_wrap_up(self, state: InterviewState) -> str:
        """Generate the wrap-up message.
        
        Args:
            state: Current interview state
        
        Returns:
            Wrap-up message
        """
        prompt = f"""## Task
Generate a warm wrap-up message for the interview.

## Candidate
Name: {state.profile.name}
Role: {state.profile.role}
Questions answered: {state.flags.questions_asked_count}

## Instructions
1. Thank them for their time
2. Mention that you'll prepare detailed feedback
3. Be professional and encouraging
4. Keep it brief (2-3 sentences)

Respond with ONLY the wrap-up message."""

        response = llm_chat(
            system=INTERVIEWER_SYSTEM_PROMPT,
            user=prompt,
            model=self.model
        )
        
        return response


def create_interviewer(model: str = None) -> InterviewerAgent:
    """Factory function to create an Interviewer agent.
    
    Args:
        model: Optional model override
    
    Returns:
        Configured InterviewerAgent instance
    """
    return InterviewerAgent(model=model or INTERVIEWER_MODEL)
