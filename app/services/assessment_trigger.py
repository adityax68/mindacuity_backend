"""
Assessment Trigger Logic
Determines when enough information has been gathered for assessment
"""

import logging
from typing import Dict, Any, Tuple, Set
from app.services.conversation_state_manager import ConversationState, conversation_state_manager

logger = logging.getLogger(__name__)


class AssessmentTrigger:
    """
    Determines when to trigger final assessment generation
    Based on clinical completeness criteria
    """
    
    # Diagnostic dimensions organized by priority
    REQUIRED_DIMENSIONS = {
        "core": [
            "duration",      # How long symptoms have lasted
            "frequency",     # How often they occur
            "intensity"      # Severity level (1-10 scale)
        ],
        "impact": [
            "daily_impact",  # Effect on work, relationships, sleep, appetite
            "triggers"       # What causes or worsens symptoms
        ],
        "context": [
            "physical_symptoms",  # Physical manifestations
            "coping",            # What they've tried
            "support_system"     # Who they can talk to
        ]
    }
    
    # Minimum and maximum question limits
    MIN_QUESTIONS = 8
    MAX_QUESTIONS = 13
    
    # Dimension mapping (flexible matching)
    DIMENSION_ALIASES = {
        "duration": ["duration", "how_long", "time_period"],
        "frequency": ["frequency", "how_often", "occurrence"],
        "intensity": ["intensity", "severity", "scale", "level"],
        "daily_impact": ["daily_impact", "impact", "functional_impact", "daily_life", "effect"],
        "triggers": ["triggers", "causes", "situations", "events"],
        "physical_symptoms": ["physical_symptoms", "physical", "bodily", "somatic"],
        "coping": ["coping", "management", "tried", "strategies"],
        "support_system": ["support_system", "support", "help", "people"]
    }
    
    def __init__(self):
        self.state_manager = conversation_state_manager
    
    def should_trigger_assessment(self, session_id: str) -> Tuple[bool, str]:
        """
        Determine if assessment should be triggered
        
        Args:
            session_id: Session identifier
            
        Returns:
            Tuple of (should_trigger: bool, reason: str)
        """
        state = self.state_manager.get_state(session_id)
        
        # Check maximum questions limit (hard stop)
        if state.questions_asked >= self.MAX_QUESTIONS:
            logger.info(f"Assessment triggered for {session_id}: max questions reached ({self.MAX_QUESTIONS})")
            return True, "max_questions_reached"
        
        # Check minimum questions requirement
        if state.questions_asked < self.MIN_QUESTIONS:
            return False, "insufficient_questions"
        
        # Check dimension coverage
        coverage = self._check_dimension_coverage(state.dimensions_answered)
        
        if coverage["is_complete"]:
            logger.info(
                f"Assessment triggered for {session_id}: criteria met "
                f"(Q: {state.questions_asked}, Dimensions: {len(state.dimensions_answered)})"
            )
            return True, "criteria_met"
        
        # Not ready yet
        return False, f"continue_gathering (need: {coverage['missing']})"
    
    def _check_dimension_coverage(self, answered_dimensions: Set[str]) -> Dict[str, Any]:
        """
        Check if enough dimensions have been covered
        
        Returns:
            Dict with "is_complete", "core_count", "impact_count", "context_count", "missing"
        """
        # Normalize answered dimensions
        normalized = self._normalize_dimensions(answered_dimensions)
        
        # Count coverage in each category
        core_count = sum(
            1 for dim in self.REQUIRED_DIMENSIONS["core"]
            if dim in normalized
        )
        
        impact_count = sum(
            1 for dim in self.REQUIRED_DIMENSIONS["impact"]
            if dim in normalized
        )
        
        context_count = sum(
            1 for dim in self.REQUIRED_DIMENSIONS["context"]
            if dim in normalized
        )
        
        # Determine if complete
        is_complete = (
            core_count >= 3 and      # All core dimensions
            impact_count >= 2 and    # At least 2 impact dimensions
            context_count >= 1       # At least 1 context dimension
        )
        
        # Identify missing critical dimensions
        missing = []
        if core_count < 3:
            missing.extend([
                dim for dim in self.REQUIRED_DIMENSIONS["core"]
                if dim not in normalized
            ])
        if impact_count < 2:
            missing.extend([
                dim for dim in self.REQUIRED_DIMENSIONS["impact"]
                if dim not in normalized
            ][:2 - impact_count])
        if context_count < 1:
            missing.append(self.REQUIRED_DIMENSIONS["context"][0])
        
        return {
            "is_complete": is_complete,
            "core_count": core_count,
            "impact_count": impact_count,
            "context_count": context_count,
            "total_answered": len(normalized),
            "missing": missing
        }
    
    def _normalize_dimensions(self, dimensions: Set[str]) -> Set[str]:
        """
        Normalize dimension names using aliases
        E.g., "how_long" -> "duration"
        """
        normalized = set()
        
        for answered in dimensions:
            answered_lower = answered.lower().replace(" ", "_")
            
            # Find matching canonical dimension
            for canonical, aliases in self.DIMENSION_ALIASES.items():
                if answered_lower in aliases or answered_lower == canonical:
                    normalized.add(canonical)
                    break
            else:
                # Keep original if no match found
                normalized.add(answered_lower)
        
        return normalized
    
    def get_next_dimension_needed(self, session_id: str) -> str:
        """
        Determine which dimension should be explored next
        Priority: core > impact > context
        
        Returns:
            Dimension name to explore
        """
        state = self.state_manager.get_state(session_id)
        normalized = self._normalize_dimensions(state.dimensions_answered)
        
        # Check core dimensions first
        for dim in self.REQUIRED_DIMENSIONS["core"]:
            if dim not in normalized:
                return dim
        
        # Then impact dimensions
        for dim in self.REQUIRED_DIMENSIONS["impact"]:
            if dim not in normalized:
                return dim
        
        # Finally context dimensions
        for dim in self.REQUIRED_DIMENSIONS["context"]:
            if dim not in normalized:
                return dim
        
        # All required dimensions covered, pick any remaining context dimension
        return "support_system"
    
    def get_assessment_readiness_score(self, session_id: str) -> float:
        """
        Calculate a readiness score (0.0 to 1.0) for assessment
        Useful for UI progress indicators
        
        Returns:
            Float between 0.0 (not ready) and 1.0 (fully ready)
        """
        state = self.state_manager.get_state(session_id)
        
        # Question progress (0-40% of score)
        question_progress = min(state.questions_asked / self.MIN_QUESTIONS, 1.0) * 0.4
        
        # Dimension coverage (0-60% of score)
        coverage = self._check_dimension_coverage(state.dimensions_answered)
        
        core_weight = 0.3
        impact_weight = 0.2
        context_weight = 0.1
        
        core_score = (coverage["core_count"] / 3) * core_weight
        impact_score = (coverage["impact_count"] / 2) * impact_weight
        context_score = (coverage["context_count"] / 1) * context_weight
        
        dimension_progress = core_score + impact_score + context_score
        
        total_score = question_progress + dimension_progress
        
        return min(total_score, 1.0)
    
    def get_assessment_status(self, session_id: str) -> Dict[str, Any]:
        """
        Get detailed assessment status for debugging/logging
        
        Returns:
            Dict with comprehensive status information
        """
        state = self.state_manager.get_state(session_id)
        should_trigger, reason = self.should_trigger_assessment(session_id)
        coverage = self._check_dimension_coverage(state.dimensions_answered)
        readiness_score = self.get_assessment_readiness_score(session_id)
        
        return {
            "should_trigger": should_trigger,
            "trigger_reason": reason,
            "questions_asked": state.questions_asked,
            "min_questions": self.MIN_QUESTIONS,
            "max_questions": self.MAX_QUESTIONS,
            "dimensions_answered": len(state.dimensions_answered),
            "dimension_coverage": coverage,
            "readiness_score": readiness_score,
            "next_dimension_needed": self.get_next_dimension_needed(session_id) if not should_trigger else None
        }
    
    def mark_dimension_answered(
        self,
        session_id: str,
        dimension: str,
        answer: Any
    ) -> bool:
        """
        Mark a dimension as answered and update state
        
        Args:
            session_id: Session identifier
            dimension: Dimension name (will be normalized)
            answer: User's answer
            
        Returns:
            True if successful
        """
        try:
            # Normalize dimension name
            normalized_dim = self._normalize_single_dimension(dimension)
            
            # Update state
            return self.state_manager.add_answer(session_id, normalized_dim, answer)
            
        except Exception as e:
            logger.error(f"Error marking dimension answered for {session_id}: {e}")
            return False
    
    def _normalize_single_dimension(self, dimension: str) -> str:
        """
        Normalize a single dimension name
        """
        dimension_lower = dimension.lower().replace(" ", "_")
        
        for canonical, aliases in self.DIMENSION_ALIASES.items():
            if dimension_lower in aliases or dimension_lower == canonical:
                return canonical
        
        return dimension_lower
    
    def can_skip_to_assessment(self, session_id: str) -> bool:
        """
        Check if we can skip remaining questions and go straight to assessment
        Useful for cases where user provides comprehensive initial description
        
        Returns:
            True if enough core information is present
        """
        state = self.state_manager.get_state(session_id)
        
        # Need at least min questions
        if state.questions_asked < self.MIN_QUESTIONS:
            return False
        
        # Need all core dimensions
        normalized = self._normalize_dimensions(state.dimensions_answered)
        core_complete = all(
            dim in normalized
            for dim in self.REQUIRED_DIMENSIONS["core"]
        )
        
        return core_complete


# Global instance
assessment_trigger = AssessmentTrigger()

