"""Workflow for Interview Coach system.

This module provides a simple workflow implementation that can work
without LangGraph. The workflow pattern follows:
    User Message -> Observer (hybrid pipeline) -> Interviewer -> Logger -> (repeat or end)

The Observer uses a hybrid pipeline by default:
    1. InputClassifier + HallucinationGuard run in parallel (gpt-5-mini)
    2. GraderPlanner runs with their results (gpt-5.2)
    
This provides structured internal_thoughts for better logging while 
maintaining quality and reducing costs.
"""

from typing import Optional

from .schemas import (
    InterviewState, 
    CandidateProfile, 
    Turn, 
    InputType, 
    NextAction,
    InterviewFlags
)
from .agents.observer import ObserverAgent
from .agents.interviewer import InterviewerAgent
from .agents.hiring_manager import HiringManagerAgent
from .logger import InterviewLogger, format_internal_thoughts


class InterviewSession:
    """High-level interface for running interview sessions.
    
    This class manages the interview workflow:
    1. User sends a message
    2. Observer analyzes the message (hidden reflection) using hybrid pipeline
    3. Interviewer generates a response based on Observer's directive
    4. The turn is logged
    5. Repeat until STOP command
    6. HiringManager generates final report
    
    The Observer uses a hybrid pipeline by default:
    - InputClassifier + HallucinationGuard run in parallel (fast model)
    - GraderPlanner runs with their results (smart model)
    """
    
    def __init__(self, profile: CandidateProfile, use_hybrid_observer: bool = True):
        """Initialize an interview session.
        
        Args:
            profile: Candidate profile information
            use_hybrid_observer: If True, use the hybrid Observer pipeline (default).
                                 The hybrid pipeline runs classification and 
                                 hallucination detection in parallel on a fast model,
                                 then scoring/planning on a smart model.
        """
        self.profile = profile
        self.use_hybrid_observer = use_hybrid_observer
        
        # Initialize state
        self.state = InterviewState(
            profile=profile,
            flags=InterviewFlags()
        )
        
        # Initialize logger
        self.logger = InterviewLogger(profile.name)
        self.logger.set_metadata(
            role=profile.role,
            grade_target=profile.grade_target,
            experience=profile.experience
        )
        
        # Initialize agents
        self.observer = ObserverAgent(use_hybrid=use_hybrid_observer)
        self.interviewer = InterviewerAgent()
        self.hiring_manager = HiringManagerAgent()
        
        # Track state
        self._is_finished = False
        self._turn_count = 0
    
    def process_message(self, user_message: str) -> str:
        """Process a user message and get the interviewer's response.
        
        This is the main workflow:
        1. Observer analyzes the message
        2. Update state based on Observer's directive
        3. Interviewer generates response
        4. Log the turn
        5. Check if interview should end
        
        Args:
            user_message: The user's input
        
        Returns:
            The interviewer's response
        """
        # Step 1: Observer analyzes the message
        directive = self.observer.analyze(self.state, user_message)
        
        # Step 2: Update state from Observer's analysis
        self._update_state_from_directive(directive, user_message)
        
        # Step 3: Check for STOP before generating response
        if directive.input_type == InputType.STOP:
            self._is_finished = True
            # Generate wrap-up response
            response = self.interviewer.respond(self.state, directive)
            self.state.current_agent_response = response
            
            # Log the turn
            self._log_turn(user_message, response, directive)
            
            # Generate final report
            self._generate_final_report()
            
            return response
        
        # Step 4: Interviewer generates response
        response = self.interviewer.respond(self.state, directive)
        self.state.current_agent_response = response
        
        # Step 5: Update state after response
        self._update_state_after_response(directive)
        
        # Step 6: Log the turn
        self._log_turn(user_message, response, directive)
        
        return response
    
    def _update_state_from_directive(self, directive, user_message: str) -> None:
        """Update interview state based on Observer's directive.
        
        Args:
            directive: ObserverDirective from Observer
            user_message: The user's message
        """
        self.state.current_directive = directive
        self.state.current_user_message = user_message
        
        # Update flags
        if directive.input_type == InputType.OFF_TOPIC:
            self.state.flags.off_topic_count += 1
        if directive.is_hallucination:
            self.state.flags.hallucination_claims += 1
        
        # Update topic scores if it was an answer
        if directive.input_type == InputType.ANSWER and directive.next_topic:
            self.state.update_topic_score(
                topic=directive.next_topic,
                score=directive.answer_score,
                gaps=directive.gaps_found,
                correct_answer=directive.correct_answer_for_gaps
            )
        
        # Track soft skills
        self.state.soft_scores.append(directive.soft_signals)
    
    def _update_state_after_response(self, directive) -> None:
        """Update state after Interviewer response.
        
        Args:
            directive: ObserverDirective that was used
        """
        # Update difficulty
        new_difficulty = self.state.difficulty + directive.difficulty_delta
        self.state.difficulty = max(1, min(5, new_difficulty))
        
        # Update current topic
        if directive.next_topic:
            self.state.current_topic = directive.next_topic
        
        # Track questions asked
        if directive.next_action in [NextAction.ASK, NextAction.FOLLOW_UP]:
            self.state.flags.questions_asked_count += 1
            if directive.question_blueprint:
                self.state.last_questions.append(directive.question_blueprint)
                self.state.last_questions = self.state.last_questions[-5:]
    
    def _log_turn(self, user_message: str, response: str, directive) -> None:
        """Log a turn to both state and logger.
        
        Args:
            user_message: The user's message
            response: The interviewer's response
            directive: The directive used
        """
        self._turn_count += 1
        
        # Format internal thoughts per ТЗ requirements
        internal_thoughts = format_internal_thoughts(
            observer_thoughts=directive.internal_thoughts,
            interviewer_action=directive.next_action.value,
            difficulty=self.state.difficulty,
            topic=directive.next_topic,
            score=directive.answer_score if directive.input_type == InputType.ANSWER else None,
            is_final=(directive.input_type == InputType.STOP)
        )
        
        # Create turn object
        turn = Turn(
            turn_id=self._turn_count,
            agent_visible_message=response,
            user_message=user_message,
            internal_thoughts=internal_thoughts,
            topic=directive.next_topic,
            score=directive.answer_score if directive.input_type == InputType.ANSWER else None
        )
        
        # Add to state
        self.state.turns.append(turn)
        
        # Add to logger
        self.logger.add_turn(
            turn_id=self._turn_count,
            agent_visible_message=response,
            user_message=user_message,
            internal_thoughts=internal_thoughts
        )
    
    def _generate_final_report(self) -> None:
        """Generate and store the final report."""
        report = self.hiring_manager.generate_report(self.state)
        self.state.final_feedback = report
        self.logger.set_feedback(report)
    
    def is_finished(self) -> bool:
        """Check if the interview is finished.
        
        Returns:
            True if interview is complete
        """
        return self._is_finished
    
    def get_final_feedback(self) -> Optional[str]:
        """Get the final feedback report.
        
        Returns:
            The final report, or None if not finished
        """
        return self.state.final_feedback
    
    def save_log(self, path: str = None) -> str:
        """Save the interview log to a file.
        
        Args:
            path: Output file path
        
        Returns:
            The path where the file was saved
        """
        return self.logger.save(path)
    
    def get_state(self) -> InterviewState:
        """Get the current interview state.
        
        Returns:
            Current InterviewState
        """
        return self.state
    
    def get_turn_count(self) -> int:
        """Get the number of turns completed.
        
        Returns:
            Number of turns
        """
        return self._turn_count


# Optional: LangGraph-based implementation (if langgraph is available)
try:
    from langgraph.graph import StateGraph, END
    from typing import TypedDict, Literal
    
    class GraphState(TypedDict):
        """State for the LangGraph workflow."""
        interview_state: InterviewState
        logger: InterviewLogger
        current_user_message: str
        should_end: bool
    
    def build_interview_graph():
        """Build a LangGraph-based workflow (optional).
        
        This provides an alternative implementation using LangGraph
        for more complex workflow needs.
        """
        # This is provided for compatibility but InterviewSession
        # above is the recommended interface
        raise NotImplementedError(
            "LangGraph implementation available but InterviewSession "
            "class is recommended for simplicity."
        )
    
    LANGGRAPH_AVAILABLE = True

except ImportError:
    LANGGRAPH_AVAILABLE = False
    
    def build_interview_graph():
        raise ImportError(
            "LangGraph is not installed. Use InterviewSession class instead. "
            "Install with: pip install langgraph"
        )
