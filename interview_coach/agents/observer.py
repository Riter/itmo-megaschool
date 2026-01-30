"""Observer Agent - Hidden reflection and analysis.

This module implements the Observer agent using a hybrid pipeline:
1. InputClassifier + HallucinationGuard run in parallel (gpt-5-mini)
2. GraderPlanner runs with their results (gpt-5.2)

This provides better logs, cost savings, while maintaining quality.
"""

import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional

from ..config import llm_chat, OBSERVER_MODEL
from ..schemas import (
    InterviewState, 
    ObserverDirective,
    InputClassification,
    HallucinationResult,
    InputType, 
    NextAction,
    SoftSignals
)
from .observer_steps import InputClassifier, HallucinationGuard, GraderPlanner


# Legacy single-call prompt (kept for fallback)
OBSERVER_SYSTEM_PROMPT = """You are the Observer agent in a technical interview system.
Your role is to analyze candidate responses PRIVATELY and provide instructions to the Interviewer.
The candidate NEVER sees your output - only the Interviewer does.

## Your Tasks (execute ALL steps in order, show reasoning for each):

### Step 1: Input Classification
Classify the user message into ONE of these types:
- ANSWER: Response to an interview question (technical or about experience)
- CANDIDATE_QUESTION: Candidate asking about the job, company, tasks, etc.
- OFF_TOPIC: Irrelevant content (weather, jokes, personal questions to interviewer, etc.)
- STOP: Interview termination request (contains "стоп", "хватит", "завершить", "стоп игра", etc.)
- GREETING: Initial introduction or hello

### Step 2: Hallucination Detection
Check for confident FALSE technical claims. Flag as hallucination if candidate states something factually wrong with confidence.
Examples of hallucinations:
- "Python 4.0 will remove for-loops" -> HALLUCINATION (Python 4.0 doesn't exist, for-loops are core)
- "Django uses async by default since version 2" -> HALLUCINATION (Django async support is opt-in)
- "JavaScript is compiled to machine code directly" -> HALLUCINATION (JS is interpreted/JIT compiled)

If hallucination detected:
- Set is_hallucination=true
- Provide hallucination_correction with the CORRECT information
- The Interviewer will politely correct the candidate

### Step 3: Answer Evaluation (if input_type is ANSWER)
Score the answer 0.0-1.0 based on:
- Correctness of technical facts (50%)
- Completeness of explanation (30%)
- Relevance to the question asked (20%)

Identify specific GAPS - what the candidate missed or got wrong.
Provide the CORRECT answer explanation for any gaps found.

Scoring guide:
- 0.9-1.0: Excellent, comprehensive answer
- 0.7-0.8: Good answer with minor omissions
- 0.5-0.6: Partial answer, significant gaps
- 0.3-0.4: Weak answer, major misunderstandings
- 0.0-0.2: Incorrect or "I don't know"

### Step 4: Soft Skills Assessment
Evaluate (each 0.0-1.0):
- clarity: How well-structured and clear is the explanation?
- honesty: Did they admit not knowing (good) vs making things up (bad)?
- engagement: Did they show interest, ask clarifying questions?

### Step 5: Next Action Planning
Based on ALL the above, decide the next action:

| Situation | Action | Notes |
|-----------|--------|-------|
| input_type=GREETING | ASK | Start with introduction, then first question |
| input_type=ANSWER, score>=0.8 (2x in row) | ASK/FOLLOW_UP | Increase difficulty, go deeper |
| input_type=ANSWER, score>=0.6 | ASK | Continue to next topic/question |
| input_type=ANSWER, score<0.5 | GIVE_HINT or ASK | Decrease difficulty or give hint |
| input_type=CANDIDATE_QUESTION | ANSWER_CANDIDATE | Answer briefly, then return to interview |
| is_hallucination=true | CORRECT_HALLUCINATION | Politely correct, provide truth |
| input_type=OFF_TOPIC | REDIRECT_TO_INTERVIEW | Acknowledge briefly, redirect |
| input_type=STOP | WRAP_UP | Thank and end interview |

### Step 6: Question Blueprint
If next_action is ASK or FOLLOW_UP, provide question_blueprint:
- What topic to cover
- What aspect to focus on
- Example question structure

## Context Awareness Rules (CRITICAL):
1. Check last_questions - DO NOT repeat questions already asked
2. Check facts_about_candidate - DO NOT ask about things they already mentioned
3. Keep track of topics covered - ensure variety
4. Match question difficulty to current difficulty level (1-5)

## Output Format
Return ONLY valid JSON matching the ObserverDirective schema. Include internal_thoughts with your full reasoning chain."""


class ObserverAgent:
    """Observer agent that analyzes candidate responses and directs the Interviewer.
    
    This agent performs hidden reflection - its output is never shown to the candidate.
    It uses a hybrid pipeline:
    1. InputClassifier + HallucinationGuard run in parallel (fast/cheap model)
    2. GraderPlanner runs with their results (smart model)
    
    Falls back to single-call mode if hybrid pipeline fails.
    """
    
    def __init__(self, model: str = OBSERVER_MODEL, use_hybrid: bool = True):
        """Initialize the Observer agent.
        
        Args:
            model: LLM model to use (for legacy single-call mode)
            use_hybrid: If True, use the hybrid pipeline (default)
        """
        self.model = model
        self.use_hybrid = use_hybrid
        
        # Initialize pipeline components
        if use_hybrid:
            self.classifier = InputClassifier()
            self.hallucination_guard = HallucinationGuard()
            self.grader_planner = GraderPlanner()
    
    def analyze(self, state: InterviewState, user_message: str) -> ObserverDirective:
        """Analyze user message and generate directive for Interviewer.
        
        Args:
            state: Current interview state
            user_message: The user's input message
        
        Returns:
            ObserverDirective with classification, scoring, and next action
        """
        if self.use_hybrid:
            try:
                directive = self._analyze_hybrid(state, user_message)
            except Exception as e:
                # Fallback to single-call mode
                directive = self._analyze_single_call(state, user_message)
                directive.internal_thoughts = (
                    f"[Hybrid pipeline failed: {str(e)}] " + 
                    directive.internal_thoughts
                )
        else:
            directive = self._analyze_single_call(state, user_message)
        
        # Apply difficulty adaptation logic
        directive = self._apply_difficulty_rules(state, directive)
        
        return directive
    
    def _analyze_hybrid(self, state: InterviewState, user_message: str) -> ObserverDirective:
        """Analyze using the hybrid pipeline with parallel steps.
        
        Args:
            state: Current interview state
            user_message: The user's input
        
        Returns:
            ObserverDirective from the hybrid pipeline
        """
        # Step 1: Run InputClassifier and HallucinationGuard in parallel
        with ThreadPoolExecutor(max_workers=2) as executor:
            future_classify = executor.submit(
                self.classifier.classify, state, user_message
            )
            future_hallucination = executor.submit(
                self.hallucination_guard.check, state, user_message
            )
            
            classification = future_classify.result()
            hallucination = future_hallucination.result()
        
        # Step 2: Run GraderPlanner with results from step 1
        directive = self.grader_planner.plan(
            state, user_message, classification, hallucination
        )
        
        # Step 3: Format structured internal_thoughts for better logging
        directive.internal_thoughts = self._format_structured_thoughts(
            classification, hallucination, directive.internal_thoughts
        )
        
        return directive
    
    def _format_structured_thoughts(
        self,
        classification: InputClassification,
        hallucination: HallucinationResult,
        grader_thoughts: str
    ) -> str:
        """Format internal thoughts as readable summary for logging.
        
        Output format is a JSON object that can be parsed by the logger,
        but also remains human-readable.
        
        Args:
            classification: Result from InputClassifier
            hallucination: Result from HallucinationGuard
            grader_thoughts: Reasoning from GraderPlanner
        
        Returns:
            JSON string with structured thoughts
        """
        thoughts = {
            "InputClassifier": {
                "type": classification.input_type.value,
                "entities": classification.detected_entities[:5] if classification.detected_entities else [],
                "reasoning": classification.reasoning[:100] if classification.reasoning else ""
            },
            "HallucinationGuard": {
                "detected": hallucination.is_hallucination,
                "claim": hallucination.detected_claim[:100] if hallucination.detected_claim else None,
                "correction": hallucination.correction[:150] if hallucination.correction else None
            },
            "GraderPlanner": {
                "reasoning": grader_thoughts[:200] if grader_thoughts else ""
            }
        }
        
        return json.dumps(thoughts, ensure_ascii=False, indent=2)
    
    def _analyze_single_call(self, state: InterviewState, user_message: str) -> ObserverDirective:
        """Analyze using the legacy single-call approach.
        
        Args:
            state: Current interview state
            user_message: The user's input
        
        Returns:
            ObserverDirective from single LLM call
        """
        # Build context for the Observer
        context = self._build_context(state, user_message)
        
        # Call LLM with JSON mode
        response = llm_chat(
            system=OBSERVER_SYSTEM_PROMPT,
            user=context,
            model=self.model,
            json_mode=True
        )
        
        # Parse response into directive
        return self._parse_response(response, user_message)
    
    def _build_context(self, state: InterviewState, user_message: str) -> str:
        """Build the context message for the LLM.
        
        Args:
            state: Current interview state
            user_message: The user's input
        
        Returns:
            Formatted context string
        """
        parts = [
            "## Interview Context",
            state.get_context_summary(),
            "",
            "## Recent Conversation",
            state.get_conversation_history(last_n=5),
            "",
            "## Current User Message",
            f'"{user_message}"',
            "",
            "## Your Task",
            "Analyze the user message and provide an ObserverDirective as JSON.",
            "Follow ALL 6 steps in your reasoning.",
        ]
        
        # Add recent scores for difficulty adaptation
        recent_scores = state.get_recent_scores(3)
        if recent_scores:
            parts.append(f"\n## Recent Answer Scores: {recent_scores}")
        
        return "\n".join(parts)
    
    def _parse_response(self, response: str, user_message: str) -> ObserverDirective:
        """Parse the LLM response into an ObserverDirective.
        
        Args:
            response: Raw LLM response (should be JSON)
            user_message: Original user message (for fallback)
        
        Returns:
            Parsed ObserverDirective
        """
        try:
            data = json.loads(response)
            
            # Replace null values with defaults (LLM returns null, Pydantic needs actual values)
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
            
            # Handle soft_signals conversion
            if "soft_signals" in data and isinstance(data["soft_signals"], dict):
                data["soft_signals"] = SoftSignals(**data["soft_signals"])
            elif "soft_signals" not in data or data["soft_signals"] is None:
                data["soft_signals"] = SoftSignals()
            
            # Handle enum conversion
            if "input_type" in data:
                data["input_type"] = InputType(data["input_type"])
            if "next_action" in data:
                data["next_action"] = NextAction(data["next_action"])
            
            return ObserverDirective(**data)
            
        except (json.JSONDecodeError, ValueError) as e:
            # Fallback directive if parsing fails
            return self._create_fallback_directive(user_message, str(e))
    
    def _create_fallback_directive(self, user_message: str, error: str) -> ObserverDirective:
        """Create a fallback directive when parsing fails.
        
        Args:
            user_message: The original user message
            error: Error message from parsing
        
        Returns:
            Safe fallback directive
        """
        # Try to detect STOP command manually
        stop_keywords = ["стоп", "хватит", "завершить", "stop", "стоп игра"]
        is_stop = any(kw in user_message.lower() for kw in stop_keywords)
        
        if is_stop:
            return ObserverDirective(
                input_type=InputType.STOP,
                next_action=NextAction.WRAP_UP,
                internal_thoughts=f"[Fallback] Detected STOP command. Parse error: {error}"
            )
        
        return ObserverDirective(
            input_type=InputType.ANSWER,
            next_action=NextAction.ASK,
            answer_score=0.5,
            internal_thoughts=f"[Fallback] Failed to parse LLM response: {error}. Continuing with default action."
        )
    
    def _apply_difficulty_rules(
        self, 
        state: InterviewState, 
        directive: ObserverDirective
    ) -> ObserverDirective:
        """Apply difficulty adaptation rules with hysteresis.
        
        Args:
            state: Current interview state
            directive: The parsed directive
        
        Returns:
            Directive with adjusted difficulty_delta
        """
        if directive.input_type not in [InputType.ANSWER, InputType.GREETING]:
            return directive
        
        recent_scores = state.get_recent_scores(2)
        
        # Need at least 2 scores for hysteresis
        if len(recent_scores) < 2:
            return directive
        
        # Check for consistent high performance
        if all(s >= 0.8 for s in recent_scores) and state.difficulty < 5:
            directive.difficulty_delta = 1
            # Append to internal_thoughts (handle both string and JSON formats)
            if directive.internal_thoughts.startswith("{"):
                try:
                    thoughts = json.loads(directive.internal_thoughts)
                    thoughts["DifficultyAdapter"] = "Increased difficulty: 2 consecutive high scores"
                    directive.internal_thoughts = json.dumps(thoughts, ensure_ascii=False, indent=2)
                except json.JSONDecodeError:
                    directive.internal_thoughts += " [Difficulty++: 2 consecutive high scores]"
            else:
                directive.internal_thoughts += " [Difficulty++: 2 consecutive high scores]"
        
        # Check for consistent low performance  
        elif all(s <= 0.4 for s in recent_scores) and state.difficulty > 1:
            directive.difficulty_delta = -1
            if directive.internal_thoughts.startswith("{"):
                try:
                    thoughts = json.loads(directive.internal_thoughts)
                    thoughts["DifficultyAdapter"] = "Decreased difficulty: 2 consecutive low scores"
                    directive.internal_thoughts = json.dumps(thoughts, ensure_ascii=False, indent=2)
                except json.JSONDecodeError:
                    directive.internal_thoughts += " [Difficulty--: 2 consecutive low scores]"
            else:
                directive.internal_thoughts += " [Difficulty--: 2 consecutive low scores]"
        
        # Single very low score - suggest hint instead of difficulty change
        elif directive.answer_score <= 0.3 and directive.next_action == NextAction.ASK:
            directive.next_action = NextAction.GIVE_HINT
            if directive.internal_thoughts.startswith("{"):
                try:
                    thoughts = json.loads(directive.internal_thoughts)
                    thoughts["DifficultyAdapter"] = "Changed action to GIVE_HINT: very low score"
                    directive.internal_thoughts = json.dumps(thoughts, ensure_ascii=False, indent=2)
                except json.JSONDecodeError:
                    directive.internal_thoughts += " [Action->GIVE_HINT: very low score]"
            else:
                directive.internal_thoughts += " [Action->GIVE_HINT: very low score]"
        
        return directive


def create_observer(model: str = None, use_hybrid: bool = True) -> ObserverAgent:
    """Factory function to create an Observer agent.
    
    Args:
        model: Optional model override (for legacy single-call mode)
        use_hybrid: If True, use the hybrid pipeline (default)
    
    Returns:
        Configured ObserverAgent instance
    """
    return ObserverAgent(model=model or OBSERVER_MODEL, use_hybrid=use_hybrid)
