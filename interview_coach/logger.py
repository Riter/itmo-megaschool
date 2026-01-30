"""Interview session logger for JSON output."""

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Optional, Any

from .schemas import InterviewState, Turn


# Default logs directory
LOGS_DIR = Path(__file__).parent.parent / "logs"


def get_next_log_path(logs_dir: Path = None, prefix: str = "interview_log") -> Path:
    """Get the next available log file path with incrementing number.
    
    Args:
        logs_dir: Directory to save logs (default: logs/)
        prefix: Prefix for log files (default: interview_log)
    
    Returns:
        Path to the next log file (e.g., logs/interview_log_3.json)
    """
    if logs_dir is None:
        logs_dir = LOGS_DIR
    
    # Create logs directory if it doesn't exist
    logs_dir.mkdir(parents=True, exist_ok=True)
    
    # Find existing log files and get the highest number
    pattern = re.compile(rf"^{re.escape(prefix)}_(\d+)\.json$")
    max_num = 0
    
    for file in logs_dir.iterdir():
        if file.is_file():
            match = pattern.match(file.name)
            if match:
                num = int(match.group(1))
                max_num = max(max_num, num)
    
    # Return next number
    next_num = max_num + 1
    return logs_dir / f"{prefix}_{next_num}.json"


class InterviewLogger:
    """Logger for interview sessions that outputs to JSON format as per ТЗ requirements.
    
    Output format:
    {
        "participant_name": "...",
        "turns": [
            {
                "turn_id": 1,
                "agent_visible_message": "...",
                "user_message": "...",
                "internal_thoughts": "[Observer]: ... [Interviewer]: ..."
            }
        ],
        "final_feedback": "..."
    }
    """
    
    def __init__(self, participant_name: str):
        """Initialize the logger.
        
        Args:
            participant_name: Name of the interview candidate
        """
        self.participant_name = participant_name
        self.turns: list[dict[str, Any]] = []
        self.final_feedback: Optional[str] = None
        self.metadata: dict[str, Any] = {
            "started_at": datetime.now().isoformat(),
            "role": None,
            "grade_target": None,
        }
    
    def set_metadata(self, role: str, grade_target: str, experience: str = None) -> None:
        """Set interview metadata.
        
        Args:
            role: Position being interviewed for
            grade_target: Target grade level
            experience: Candidate's experience description
        """
        self.metadata["role"] = role
        self.metadata["grade_target"] = grade_target
        if experience:
            self.metadata["experience"] = experience
    
    def add_turn(
        self, 
        turn_id: int, 
        agent_visible_message: str, 
        user_message: str, 
        internal_thoughts: str
    ) -> None:
        """Add a turn to the log.
        
        Args:
            turn_id: Sequential turn number
            agent_visible_message: The message shown to the user from Interviewer
            user_message: The user's input
            internal_thoughts: Hidden reasoning from Observer and Interviewer
        """
        self.turns.append({
            "turn_id": turn_id,
            "agent_visible_message": agent_visible_message,
            "user_message": user_message,
            "internal_thoughts": internal_thoughts
        })
    
    def add_turn_from_state(self, state: InterviewState) -> None:
        """Add a turn from the current interview state.
        
        Args:
            state: Current interview state with turn data
        """
        if state.turns:
            latest_turn = state.turns[-1]
            # Avoid duplicates
            if not self.turns or self.turns[-1]["turn_id"] != latest_turn.turn_id:
                self.add_turn(
                    turn_id=latest_turn.turn_id,
                    agent_visible_message=latest_turn.agent_visible_message,
                    user_message=latest_turn.user_message,
                    internal_thoughts=latest_turn.internal_thoughts
                )
    
    def set_feedback(self, feedback: str) -> None:
        """Set the final feedback report.
        
        Args:
            feedback: The complete final feedback from HiringManager
        """
        self.final_feedback = feedback
        self.metadata["finished_at"] = datetime.now().isoformat()
    
    def to_dict(self) -> dict[str, Any]:
        """Convert the log to a dictionary.
        
        Returns:
            Dictionary in the required format
        """
        return {
            "participant_name": self.participant_name,
            "turns": self.turns,
            "final_feedback": self.final_feedback
        }
    
    def to_dict_with_metadata(self) -> dict[str, Any]:
        """Convert the log to a dictionary with metadata.
        
        Returns:
            Dictionary with metadata included
        """
        return {
            "participant_name": self.participant_name,
            "metadata": self.metadata,
            "turns": self.turns,
            "final_feedback": self.final_feedback
        }
    
    def save(self, path: str = None, include_metadata: bool = False) -> str:
        """Save the log to a JSON file.
        
        If no path is provided, saves to logs/interview_log_N.json with 
        auto-incrementing N.
        
        Args:
            path: Path to save the file (optional, auto-generates if None)
            include_metadata: Whether to include metadata in output
        
        Returns:
            The path where the file was saved
        """
        if path is None:
            output_path = get_next_log_path()
        else:
            output_path = Path(path)
            # Ensure parent directory exists
            output_path.parent.mkdir(parents=True, exist_ok=True)
        
        if include_metadata:
            data = self.to_dict_with_metadata()
        else:
            data = self.to_dict()
        
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        return str(output_path.absolute())
    
    def get_internal_thoughts_summary(self) -> str:
        """Get a summary of all internal thoughts for debugging.
        
        Returns:
            Concatenated internal thoughts from all turns
        """
        thoughts = []
        for turn in self.turns:
            thoughts.append(f"Turn {turn['turn_id']}:")
            thoughts.append(turn["internal_thoughts"])
            thoughts.append("")
        return "\n".join(thoughts)
    
    def __repr__(self) -> str:
        return f"InterviewLogger(participant='{self.participant_name}', turns={len(self.turns)})"


def format_internal_thoughts(
    observer_thoughts: str,
    interviewer_action: str,
    difficulty: int = None,
    topic: str = None,
    score: float = None,
    is_final: bool = False
) -> str:
    """Format internal thoughts for logging per ТЗ requirements.
    
    Creates a format with each agent on a new line:
        [Observer]: <thoughts>\n
        [Interviewer]: <action>\n
        [HiringManager]: <note>\n  (only for final turn)
    
    Args:
        observer_thoughts: Reasoning from Observer (will be summarized)
        interviewer_action: Action taken by Interviewer (e.g., "ASK", "FOLLOW_UP")
        difficulty: Current difficulty level (1-5)
        topic: Current topic being discussed
        score: Answer score if applicable
        is_final: If True, add HiringManager line (for STOP/WRAP_UP turn)
    
    Returns:
        Formatted string with newline separators
    """
    lines = []
    
    # Observer line - summarize thoughts
    observer_summary = _summarize_observer_thoughts(observer_thoughts, topic, score)
    lines.append(f"[Observer]: {observer_summary}")
    
    # Interviewer line
    interviewer_parts = [f"Action: {interviewer_action}"]
    if difficulty is not None:
        interviewer_parts.append(f"Difficulty: {difficulty}")
    lines.append(f"[Interviewer]: {', '.join(interviewer_parts)}")
    
    # HiringManager line (only for final turn)
    if is_final:
        lines.append("[HiringManager]: Generating final feedback report")
    
    return "\n".join(lines) + "\n"


def _summarize_observer_thoughts(thoughts: str, topic: str = None, score: float = None) -> str:
    """Summarize Observer thoughts into a readable one-liner.
    
    Handles both JSON format (from hybrid pipeline) and plain string format.
    
    Args:
        thoughts: Raw Observer thoughts (may be JSON or plain string)
        topic: Current topic (fallback if not in thoughts)
        score: Answer score (fallback if not in thoughts)
    
    Returns:
        Readable summary string
    """
    # Try to parse as JSON (from hybrid pipeline)
    try:
        data = json.loads(thoughts)
        parts = []
        
        # Extract from InputClassifier
        if "InputClassifier" in data:
            classifier = data["InputClassifier"]
            if "type" in classifier:
                parts.append(f"type={classifier['type']}")
            if "entities" in classifier and classifier["entities"]:
                entities_str = str(classifier["entities"][:3])  # Limit to 3
                parts.append(f"entities={entities_str}")
        
        # Extract from HallucinationGuard
        if "HallucinationGuard" in data:
            halluc = data["HallucinationGuard"]
            if halluc.get("detected"):
                claim = halluc.get("claim", "unknown")
                parts.append(f"hallucination=TRUE: {claim[:50]}")
            else:
                parts.append("hallucination=false")
        
        # Extract from GraderPlanner
        if "GraderPlanner" in data:
            grader = data["GraderPlanner"]
            if "reasoning" in grader:
                # Just note that grading was done
                parts.append("graded")
        
        # Add topic and score if provided
        if topic:
            parts.append(f"topic={topic}")
        if score is not None:
            parts.append(f"score={score:.2f}")
        
        return ", ".join(parts) if parts else thoughts[:200]
        
    except (json.JSONDecodeError, TypeError, KeyError):
        # Plain string format - use as-is but limit length
        summary_parts = []
        
        # Add topic and score if provided
        if topic:
            summary_parts.append(f"topic={topic}")
        if score is not None:
            summary_parts.append(f"score={score:.2f}")
        
        # Add truncated thoughts
        clean_thoughts = thoughts.replace("\n", " ").strip()
        if len(clean_thoughts) > 150:
            clean_thoughts = clean_thoughts[:150] + "..."
        summary_parts.append(clean_thoughts)
        
        return ", ".join(summary_parts)
