"""Pydantic schemas for Interview Coach system."""

from pydantic import BaseModel, Field
from typing import Optional, Any
from enum import Enum


class InputType(str, Enum):
    """Types of user input that Observer can classify."""
    ANSWER = "ANSWER"
    CANDIDATE_QUESTION = "CANDIDATE_QUESTION"
    OFF_TOPIC = "OFF_TOPIC"
    STOP = "STOP"
    GREETING = "GREETING"


class NextAction(str, Enum):
    """Actions that Interviewer should take based on Observer directive."""
    ASK = "ASK"
    FOLLOW_UP = "FOLLOW_UP"
    GIVE_HINT = "GIVE_HINT"
    ANSWER_CANDIDATE = "ANSWER_CANDIDATE"
    CORRECT_HALLUCINATION = "CORRECT_HALLUCINATION"
    REDIRECT_TO_INTERVIEW = "REDIRECT_TO_INTERVIEW"
    WRAP_UP = "WRAP_UP"


class CandidateProfile(BaseModel):
    """Profile of the interview candidate."""
    name: str
    role: str = Field(description="Position, e.g. 'Backend Developer', 'ML Engineer'")
    grade_target: str = Field(description="Target grade: 'Junior', 'Middle', 'Senior'")
    experience: str = Field(description="Free-form experience description")


class TopicScore(BaseModel):
    """Tracking score and details for a specific topic."""
    asked_count: int = 0
    total_score: float = 0.0  # Accumulated score
    last_score: float = 0.0  # Most recent score
    gaps: list[str] = Field(default_factory=list)
    correct_answers: list[str] = Field(default_factory=list, description="Correct answers for gaps")
    questions_asked: list[str] = Field(default_factory=list)
    
    @property
    def average_score(self) -> float:
        """Calculate average score for this topic."""
        if self.asked_count == 0:
            return 0.0
        return self.total_score / self.asked_count


class SoftSignals(BaseModel):
    """Soft skills signals from a single turn."""
    clarity: float = Field(default=0.5, ge=0.0, le=1.0)
    honesty: float = Field(default=0.5, ge=0.0, le=1.0)
    engagement: float = Field(default=0.5, ge=0.0, le=1.0)


class InputClassification(BaseModel):
    """Result from InputClassifier step in the hybrid Observer pipeline."""
    input_type: InputType
    detected_entities: list[str] = Field(
        default_factory=list, 
        description="Technologies, topics, or keywords mentioned"
    )
    confidence: float = Field(default=0.9, ge=0.0, le=1.0)
    reasoning: str = Field(default="", description="Reasoning for classification")


class HallucinationResult(BaseModel):
    """Result from HallucinationGuard step in the hybrid Observer pipeline."""
    is_hallucination: bool = False
    detected_claim: Optional[str] = Field(
        default=None, 
        description="The false claim detected"
    )
    correction: Optional[str] = Field(
        default=None, 
        description="Correct information to replace the false claim"
    )
    confidence: float = Field(default=0.9, ge=0.0, le=1.0)
    reasoning: str = Field(default="", description="Reasoning for the detection")


class ObserverDirective(BaseModel):
    """Directive from Observer to Interviewer."""
    # Classification
    input_type: InputType
    detected_issue: Optional[str] = None
    
    # Hallucination handling
    is_hallucination: bool = False
    hallucination_correction: Optional[str] = None
    
    # Candidate question handling
    candidate_question_to_answer: Optional[str] = None
    
    # Next action planning
    next_action: NextAction
    next_topic: Optional[str] = None
    difficulty_delta: int = Field(default=0, ge=-1, le=1, description="-1, 0, or +1")
    question_blueprint: Optional[str] = Field(
        default=None, 
        description="Description of what question to ask"
    )
    
    # Context awareness
    do_not_ask: list[str] = Field(default_factory=list)
    
    # Scoring
    answer_score: float = Field(default=0.0, ge=0.0, le=1.0)
    gaps_found: list[str] = Field(default_factory=list)
    correct_answer_for_gaps: Optional[str] = Field(
        default=None,
        description="The correct answer explanation for identified gaps"
    )
    
    # Soft skills
    soft_signals: SoftSignals = Field(default_factory=SoftSignals)
    
    # Logging
    internal_thoughts: str = Field(description="Full reasoning chain for logs")


class Turn(BaseModel):
    """A single turn in the interview conversation."""
    turn_id: int
    agent_visible_message: str
    user_message: str
    internal_thoughts: str
    topic: Optional[str] = None
    score: Optional[float] = None


class InterviewFlags(BaseModel):
    """Flags tracking special events during interview."""
    off_topic_count: int = 0
    hallucination_claims: int = 0
    evasiveness: int = 0
    questions_asked_count: int = 0


class InterviewState(BaseModel):
    """Complete state of an interview session."""
    # Candidate info
    profile: CandidateProfile
    
    # Conversation history
    turns: list[Turn] = Field(default_factory=list)
    current_user_message: Optional[str] = None
    
    # Interview progress
    current_topic: Optional[str] = None
    difficulty: int = Field(default=2, ge=1, le=5, description="1-5 scale")
    topics: dict[str, TopicScore] = Field(default_factory=dict)
    
    # Context tracking
    facts_about_candidate: list[str] = Field(default_factory=list)
    last_questions: list[str] = Field(
        default_factory=list, 
        description="Last 3 questions to avoid repetition"
    )
    
    # Flags and scores
    flags: InterviewFlags = Field(default_factory=InterviewFlags)
    soft_scores: list[SoftSignals] = Field(default_factory=list)
    
    # State control
    is_finished: bool = False
    
    # Current turn data (transient)
    current_directive: Optional[ObserverDirective] = None
    current_agent_response: Optional[str] = None
    
    # Final feedback
    final_feedback: Optional[str] = None
    
    def get_recent_scores(self, n: int = 3) -> list[float]:
        """Get the last n answer scores."""
        scores = []
        for turn in reversed(self.turns):
            if turn.score is not None:
                scores.append(turn.score)
                if len(scores) >= n:
                    break
        return list(reversed(scores))
    
    def add_fact(self, fact: str) -> None:
        """Add a fact about the candidate if not already known."""
        if fact not in self.facts_about_candidate:
            self.facts_about_candidate.append(fact)
    
    def update_topic_score(
        self, 
        topic: str, 
        score: float, 
        gaps: list[str] = None,
        correct_answer: str = None,
        question: str = None
    ) -> None:
        """Update the score tracking for a topic."""
        if topic not in self.topics:
            self.topics[topic] = TopicScore()
        
        ts = self.topics[topic]
        ts.asked_count += 1
        ts.total_score += score
        ts.last_score = score
        
        if gaps:
            ts.gaps.extend(gaps)
        if correct_answer:
            ts.correct_answers.append(correct_answer)
        if question:
            ts.questions_asked.append(question)
    
    def get_context_summary(self) -> str:
        """Get a summary of the interview context for agents."""
        summary_parts = [
            f"Candidate: {self.profile.name}",
            f"Position: {self.profile.role} ({self.profile.grade_target})",
            f"Experience: {self.profile.experience}",
            f"Current difficulty: {self.difficulty}/5",
            f"Questions asked: {self.flags.questions_asked_count}",
        ]
        
        if self.facts_about_candidate:
            summary_parts.append(f"Known facts: {', '.join(self.facts_about_candidate[:5])}")
        
        if self.last_questions:
            summary_parts.append(f"Recent questions: {'; '.join(self.last_questions[-3:])}")
        
        # Topic scores
        if self.topics:
            topic_summary = []
            for topic, ts in self.topics.items():
                topic_summary.append(f"{topic}: {ts.average_score:.1f} ({ts.asked_count} q)")
            summary_parts.append(f"Topics: {', '.join(topic_summary)}")
        
        return "\n".join(summary_parts)
    
    def get_conversation_history(self, last_n: int = 5) -> str:
        """Get recent conversation history for context."""
        if not self.turns:
            return "No conversation yet."
        
        recent = self.turns[-last_n:]
        history = []
        for turn in recent:
            history.append(f"Interviewer: {turn.agent_visible_message}")
            history.append(f"Candidate: {turn.user_message}")
        
        return "\n".join(history)


class FinalReport(BaseModel):
    """Structured final interview report."""
    # Decision
    assessed_grade: str = Field(description="Junior / Middle / Senior")
    hiring_recommendation: str = Field(description="Strong Hire / Hire / No Hire")
    confidence_score: int = Field(ge=0, le=100, description="0-100%")
    
    # Technical review
    confirmed_skills: list[str] = Field(default_factory=list)
    knowledge_gaps: list[dict[str, str]] = Field(
        default_factory=list,
        description="List of {topic, gap, correct_answer}"
    )
    
    # Soft skills
    clarity_score: int = Field(ge=1, le=10)
    clarity_notes: str
    honesty_score: int = Field(ge=1, le=10)
    honesty_notes: str
    engagement_score: int = Field(ge=1, le=10)
    engagement_notes: str
    
    # Roadmap
    topics_to_study: list[str] = Field(default_factory=list)
    recommended_resources: list[str] = Field(default_factory=list)
    
    # Full text version
    full_report: str = Field(description="Complete markdown report")
