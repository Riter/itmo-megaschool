"""Hybrid Observer Pipeline Components.

This module contains the three-step hybrid pipeline for the Observer:
1. InputClassifier - classifies user message type (gpt-5-mini)
2. HallucinationGuard - detects false technical claims (gpt-5-mini)
3. GraderPlanner - scores answers and plans next action (gpt-5.2)

Steps 1 and 2 run in parallel, then step 3 receives their results.
"""

import json
from typing import Optional

from ..config import (
    llm_chat, 
    CLASSIFIER_MODEL, 
    HALLUCINATION_MODEL, 
    GRADER_PLANNER_MODEL
)
from ..schemas import (
    InterviewState,
    InputClassification,
    HallucinationResult,
    ObserverDirective,
    InputType,
    NextAction,
    SoftSignals,
)


# =============================================================================
# PROMPTS
# =============================================================================

CLASSIFIER_SYSTEM_PROMPT = """You are an input classifier for a technical interview system.
Your ONLY job is to classify the user's message into ONE category.

## Categories:
- ANSWER: Response to an interview question (technical explanation, experience description)
- CANDIDATE_QUESTION: Candidate asking about the job, company, tasks, responsibilities
- OFF_TOPIC: Irrelevant content NOT related to interview. Examples:
  * Weather talk ("какая погода?")
  * Personal questions to interviewer ("как дела?", "как ты?", "что делаешь?")
  * Jokes, small talk, random chat
  * Any "привет"/"как дела" in the MIDDLE of interview (not the first message)
- STOP: Interview termination request (contains "стоп", "хватит", "завершить", "stop", "стоп игра")
- GREETING: ONLY the FIRST message where candidate introduces themselves (name, position, experience)

## IMPORTANT Rules:
1. GREETING is ONLY for the very FIRST message of the interview
2. If questions_asked > 0 and message is "привет", "как дела?", etc. → OFF_TOPIC (not GREETING!)
3. Personal questions to interviewer = always OFF_TOPIC

## Also extract:
- detected_entities: List of technologies, topics, or keywords mentioned (e.g., ["Python", "Django", "SQL"])

## Output format (JSON only):
{
    "input_type": "ANSWER",
    "detected_entities": ["Python", "loops"],
    "confidence": 0.95,
    "reasoning": "Candidate provided technical explanation about Python control flow"
}

Be concise. Focus only on classification."""


HALLUCINATION_SYSTEM_PROMPT = """You are a fact-checker for a technical interview system.
Your ONLY job is to detect confident FALSE technical claims in the candidate's message.

## What counts as a hallucination:
- Confident statements that are factually wrong
- Made-up features, versions, or behaviors of technologies
- Incorrect technical facts stated with certainty

## Examples of hallucinations:
- "Python 4.0 will remove for-loops" → FALSE (Python 4.0 doesn't exist, for-loops are fundamental)
- "Django uses async by default since version 2" → FALSE (async is opt-in)
- "JavaScript compiles directly to machine code" → FALSE (JS is interpreted/JIT)
- "React was created by Google" → FALSE (React was created by Facebook/Meta)

## What is NOT a hallucination:
- Incorrect but hedged statements ("I think...", "maybe...")
- Opinions or preferences
- Partial or incomplete answers
- Admitting not knowing something

## Output format (JSON only):
{
    "is_hallucination": true,
    "detected_claim": "Python 4.0 will remove for-loops",
    "correction": "Python 4.0 does not exist. For-loops are a fundamental control flow construct in Python and are not being removed.",
    "confidence": 0.95,
    "reasoning": "Candidate made a confident false claim about a non-existent Python version"
}

If no hallucination detected:
{
    "is_hallucination": false,
    "detected_claim": null,
    "correction": null,
    "confidence": 0.9,
    "reasoning": "No false technical claims detected"
}

Be precise. Only flag clear factual errors."""


GRADER_PLANNER_SYSTEM_PROMPT = """You are the scoring and planning component of a technical interview system.
You receive pre-processed information and make final decisions.

## Input you receive:
1. Classification result (type of user message)
2. Hallucination check result
3. Interview context (candidate profile, history, difficulty level)

## Your tasks:

### 1. Score the answer (0.0-1.0) - only if input_type is ANSWER
- 0.9-1.0: Excellent, comprehensive answer
- 0.7-0.8: Good answer with minor omissions
- 0.5-0.6: Partial answer, significant gaps
- 0.3-0.4: Weak answer, major misunderstandings
- 0.0-0.2: Incorrect or "I don't know"

### 2. Identify gaps and provide correct answers
- List specific things the candidate missed or got wrong
- Provide the correct explanation for educational feedback

### 3. Evaluate soft skills (0.0-1.0 each)
- clarity: How well-structured and clear is the explanation?
- honesty: Did they admit not knowing (good) vs making things up (bad)?
- engagement: Did they show interest, ask clarifying questions?

### 4. Plan next action
| Situation | Action |
|-----------|--------|
| GREETING | ASK - Start with first question |
| ANSWER, score>=0.8 twice | ASK/FOLLOW_UP - Increase difficulty |
| ANSWER, score>=0.6 | ASK - Continue |
| ANSWER, score<0.5 | GIVE_HINT or ASK (simpler) |
| CANDIDATE_QUESTION | ANSWER_CANDIDATE |
| Hallucination detected | CORRECT_HALLUCINATION |
| OFF_TOPIC | REDIRECT_TO_INTERVIEW |
| STOP | WRAP_UP |

### 5. Set difficulty adjustment
- difficulty_delta: -1, 0, or +1
- Increase if two consecutive high scores (>=0.8)
- Decrease if low score (<0.5) or hallucination

### 6. Provide question blueprint (as a STRING, not object)
- A single string describing what to ask next
- Include topic, focus, and example question in the string
- Example: "Ask about Python list vs tuple differences, focus on mutability and use cases"

## Context awareness (CRITICAL):
- Check last_questions - DO NOT repeat questions
- Check facts_about_candidate - DO NOT ask what they already told you
- Keep variety in topics

## Output format (JSON only):
Return a complete ObserverDirective JSON object.

IMPORTANT: question_blueprint MUST be a string, not an object. Example:
```json
{
    "next_action": "ASK",
    "next_topic": "python_data_types",
    "question_blueprint": "Ask about list vs tuple - when to use each, mutability differences",
    "answer_score": 0.0,
    "gaps_found": [],
    "soft_signals": {"clarity": 0.5, "honesty": 0.5, "engagement": 0.5},
    "difficulty_delta": 0,
    "internal_thoughts": "Greeting received, starting with basic Python question..."
}
```"""


# =============================================================================
# COMPONENTS
# =============================================================================

class InputClassifier:
    """Classifies user message type. Runs on fast/cheap model."""
    
    def __init__(self, model: str = CLASSIFIER_MODEL):
        self.model = model
    
    def classify(self, state: InterviewState, user_message: str) -> InputClassification:
        """Classify the user message.
        
        Args:
            state: Current interview state (for context)
            user_message: The user's input
        
        Returns:
            InputClassification with type, entities, reasoning
        """
        # Build minimal context
        context = f"""## Interview Context
Candidate: {state.profile.name}
Position: {state.profile.role} ({state.profile.grade_target})
Questions asked so far: {state.flags.questions_asked_count}

## User Message
"{user_message}"

Classify this message and extract mentioned technologies/topics."""

        try:
            response = llm_chat(
                system=CLASSIFIER_SYSTEM_PROMPT,
                user=context,
                model=self.model,
                json_mode=True
            )
            
            data = json.loads(response)
            
            # Convert input_type string to enum
            input_type = InputType(data.get("input_type", "ANSWER"))
            
            return InputClassification(
                input_type=input_type,
                detected_entities=data.get("detected_entities", []),
                confidence=data.get("confidence", 0.9),
                reasoning=data.get("reasoning", "")
            )
            
        except (json.JSONDecodeError, ValueError, KeyError) as e:
            # Fallback: try to detect STOP manually
            stop_keywords = ["стоп", "хватит", "завершить", "stop", "стоп игра"]
            is_stop = any(kw in user_message.lower() for kw in stop_keywords)
            
            return InputClassification(
                input_type=InputType.STOP if is_stop else InputType.ANSWER,
                detected_entities=[],
                confidence=0.5,
                reasoning=f"[Fallback] Classification failed: {str(e)}"
            )


class HallucinationGuard:
    """Detects confident false technical claims. Runs on fast/cheap model."""
    
    def __init__(self, model: str = HALLUCINATION_MODEL):
        self.model = model
    
    def check(self, state: InterviewState, user_message: str) -> HallucinationResult:
        """Check for hallucinations in the user message.
        
        Args:
            state: Current interview state
            user_message: The user's input
        
        Returns:
            HallucinationResult with detection status and correction
        """
        # Build context with interview topic for better fact-checking
        context = f"""## Interview Context
Position: {state.profile.role}
Current topic: {state.current_topic or "general"}

## User Message to Check
"{user_message}"

Check if this message contains any confident FALSE technical claims."""

        try:
            response = llm_chat(
                system=HALLUCINATION_SYSTEM_PROMPT,
                user=context,
                model=self.model,
                json_mode=True
            )
            
            data = json.loads(response)
            
            return HallucinationResult(
                is_hallucination=data.get("is_hallucination", False),
                detected_claim=data.get("detected_claim"),
                correction=data.get("correction"),
                confidence=data.get("confidence", 0.9),
                reasoning=data.get("reasoning", "")
            )
            
        except (json.JSONDecodeError, ValueError) as e:
            # Fallback: no hallucination detected (safe default)
            return HallucinationResult(
                is_hallucination=False,
                detected_claim=None,
                correction=None,
                confidence=0.5,
                reasoning=f"[Fallback] Hallucination check failed: {str(e)}"
            )


class GraderPlanner:
    """Scores answers and plans next action. Runs on smart model."""
    
    def __init__(self, model: str = GRADER_PLANNER_MODEL):
        self.model = model
    
    def plan(
        self,
        state: InterviewState,
        user_message: str,
        classification: InputClassification,
        hallucination: HallucinationResult
    ) -> ObserverDirective:
        """Score the answer and plan the next action.
        
        Args:
            state: Current interview state
            user_message: The user's input
            classification: Result from InputClassifier
            hallucination: Result from HallucinationGuard
        
        Returns:
            Complete ObserverDirective
        """
        # Build comprehensive context
        context = self._build_context(state, user_message, classification, hallucination)
        
        try:
            response = llm_chat(
                system=GRADER_PLANNER_SYSTEM_PROMPT,
                user=context,
                model=self.model,
                json_mode=True
            )
            
            return self._parse_response(response, classification, hallucination)
            
        except Exception as e:
            # Fallback directive
            return self._create_fallback(classification, hallucination, str(e))
    
    def _build_context(
        self,
        state: InterviewState,
        user_message: str,
        classification: InputClassification,
        hallucination: HallucinationResult
    ) -> str:
        """Build context for the grader/planner."""
        
        parts = [
            "## Pre-processed Results",
            "",
            "### Classification (from InputClassifier)",
            f"- Type: {classification.input_type.value}",
            f"- Entities: {classification.detected_entities}",
            f"- Reasoning: {classification.reasoning}",
            "",
            "### Hallucination Check (from HallucinationGuard)",
            f"- Is hallucination: {hallucination.is_hallucination}",
        ]
        
        if hallucination.is_hallucination:
            parts.extend([
                f"- Detected claim: {hallucination.detected_claim}",
                f"- Correction: {hallucination.correction}",
            ])
        
        parts.extend([
            f"- Reasoning: {hallucination.reasoning}",
            "",
            "## Interview Context",
            state.get_context_summary(),
            "",
            "## Recent Conversation",
            state.get_conversation_history(last_n=5),
            "",
            "## Current User Message",
            f'"{user_message}"',
            "",
            "## Recent Answer Scores",
            str(state.get_recent_scores(3)),
            "",
            "## Your Task",
            "Based on ALL the above, provide a complete ObserverDirective JSON.",
            "Include your reasoning in internal_thoughts field.",
        ])
        
        return "\n".join(parts)
    
    def _parse_response(
        self,
        response: str,
        classification: InputClassification,
        hallucination: HallucinationResult
    ) -> ObserverDirective:
        """Parse LLM response into ObserverDirective."""
        
        data = json.loads(response)
        
        # Set defaults for null values
        defaults = {
            "answer_score": 0.0,
            "gaps_found": [],
            "do_not_ask": [],
            "difficulty_delta": 0,
            "internal_thoughts": "No reasoning provided",
        }
        for key, default in defaults.items():
            if key in data and data[key] is None:
                data[key] = default
        
        # Handle question_blueprint - LLM may return dict instead of string
        if "question_blueprint" in data and isinstance(data["question_blueprint"], dict):
            blueprint = data["question_blueprint"]
            # Convert dict to readable string
            parts = []
            if "topic" in blueprint:
                parts.append(f"Topic: {blueprint['topic']}")
            if "focus" in blueprint:
                parts.append(f"Focus: {blueprint['focus']}")
            if "question" in blueprint:
                parts.append(f"Question: {blueprint['question']}")
            if "example" in blueprint:
                parts.append(f"Example: {blueprint['example']}")
            # Include any other keys
            for key, value in blueprint.items():
                if key not in ["topic", "focus", "question", "example"]:
                    parts.append(f"{key}: {value}")
            data["question_blueprint"] = "; ".join(parts) if parts else json.dumps(blueprint)
        
        # Handle soft_signals
        if "soft_signals" in data and isinstance(data["soft_signals"], dict):
            data["soft_signals"] = SoftSignals(**data["soft_signals"])
        elif "soft_signals" not in data or data["soft_signals"] is None:
            data["soft_signals"] = SoftSignals()
        
        # Use pre-computed values from earlier steps
        data["input_type"] = classification.input_type
        data["is_hallucination"] = hallucination.is_hallucination
        data["hallucination_correction"] = hallucination.correction
        
        # Convert enums
        if "next_action" in data:
            data["next_action"] = NextAction(data["next_action"])
        
        return ObserverDirective(**data)
    
    def _create_fallback(
        self,
        classification: InputClassification,
        hallucination: HallucinationResult,
        error: str
    ) -> ObserverDirective:
        """Create a fallback directive when parsing fails."""
        
        # Determine action based on classification
        if classification.input_type == InputType.STOP:
            action = NextAction.WRAP_UP
        elif hallucination.is_hallucination:
            action = NextAction.CORRECT_HALLUCINATION
        elif classification.input_type == InputType.CANDIDATE_QUESTION:
            action = NextAction.ANSWER_CANDIDATE
        elif classification.input_type == InputType.OFF_TOPIC:
            action = NextAction.REDIRECT_TO_INTERVIEW
        else:
            action = NextAction.ASK
        
        return ObserverDirective(
            input_type=classification.input_type,
            next_action=action,
            is_hallucination=hallucination.is_hallucination,
            hallucination_correction=hallucination.correction,
            answer_score=0.5,
            internal_thoughts=f"[Fallback] GraderPlanner failed: {error}"
        )
