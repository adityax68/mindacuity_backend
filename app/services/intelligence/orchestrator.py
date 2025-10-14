"""
Conversation Orchestrator using LangGraph
State machine that controls the natural flow of mental health assessment conversations
"""

import logging
import json
from typing import Literal, Dict, Any
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langgraph.graph import StateGraph, END
from sqlalchemy.orm import Session

from app.services.intelligence.models.conversation_state import (
    ConversationState,
    ConversationStages,
    IntentTypes,
)
from app.services.intelligence.models.llm_config import TaskType
from app.services.intelligence.llm_engine import LLMEngine
from app.services.intelligence.intent_router import IntentRouter
from app.services.intelligence.memory_manager import MemoryManager
from app.services.intelligence.prompts.base_prompts import (
    BASE_SYSTEM_PROMPT,
    SENTIMENT_ANALYSIS_PROMPT,
    QUESTION_GENERATION_PROMPT,
    RESPONSE_EXTRACTION_PROMPT,
    DIAGNOSIS_ANALYSIS_PROMPT,
    DIAGNOSIS_FORMATTING_PROMPT,
    OFF_TOPIC_RESPONSE,
    CRISIS_RESPONSE_TEMPLATE,
)
from app.services.message_history_store import MessageHistoryStore

logger = logging.getLogger(__name__)


class ConversationOrchestrator:
    """
    Orchestrates the entire conversation using a state machine
    Handles natural flow between greeting, assessment, and diagnosis
    """
    
    def __init__(self):
        """Initialize orchestrator with all components"""
        self.llm_engine = LLMEngine()
        self.intent_router = IntentRouter()
        self.memory_manager = MemoryManager()
        self.graph = self._build_graph()
        
        logger.info("Conversation Orchestrator initialized with LangGraph state machine")
    
    def _build_graph(self) -> StateGraph:
        """Build the LangGraph state machine"""
        
        # Create state graph
        workflow = StateGraph(ConversationState)
        
        # Add nodes (stages of conversation)
        workflow.add_node("classify_intent", self.classify_intent_node)
        workflow.add_node("crisis_check", self.crisis_check_node)
        workflow.add_node("greeting", self.greeting_node)
        workflow.add_node("assessment", self.assessment_node)
        workflow.add_node("diagnosis", self.diagnosis_node)
        workflow.add_node("off_topic", self.off_topic_node)
        
        # Set entry point
        workflow.set_entry_point("classify_intent")
        
        # Add conditional edges based on intent
        workflow.add_conditional_edges(
            "classify_intent",
            self.route_by_intent,
            {
                "crisis": "crisis_check",
                "greeting": "greeting",
                "assessment": "assessment",
                "diagnosis": "diagnosis",
                "off_topic": "off_topic",
            }
        )
        
        # Crisis check always ends
        workflow.add_edge("crisis_check", END)
        
        # Greeting can go to assessment or end
        workflow.add_edge("greeting", END)
        
        # Assessment can loop back or go to diagnosis
        workflow.add_edge("assessment", END)
        
        # Diagnosis ends conversation
        workflow.add_edge("diagnosis", END)
        
        # Off-topic ends
        workflow.add_edge("off_topic", END)
        
        return workflow.compile()
    
    async def process_message(
        self,
        session_id: str,
        user_message: str,
        db: Session
    ) -> str:
        """
        Main entry point - process user message and return AI response
        
        Args:
            session_id: Session identifier
            user_message: User's message
            db: Database session
        
        Returns:
            AI response text
        """
        try:
            logger.info(f"Processing message for session {session_id}")
            
            # CRITICAL: Check for crisis FIRST, at every message
            crisis_result = await self.llm_engine.detect_crisis_ensemble(user_message)
            
            if crisis_result["is_crisis"]:
                logger.warning(f"CRISIS DETECTED for session {session_id}: confidence={crisis_result['confidence']}")
                
                # Save to history for tracking
                history_store = MessageHistoryStore(db=db)
                chat_history = history_store.get_chat_history(session_id)
                chat_history.add_user_message(user_message)
                chat_history.add_ai_message(CRISIS_RESPONSE_TEMPLATE)
                
                return CRISIS_RESPONSE_TEMPLATE
            
            # Load conversation state
            state = await self.memory_manager.load_state(session_id, db)
            
            # Add user message
            state["messages"].append(HumanMessage(content=user_message))
            
            # Run through state machine
            result = await self.graph.ainvoke(state)
            
            # Extract AI response (last message)
            if result["messages"] and len(result["messages"]) > 0:
                last_message = result["messages"][-1]
                ai_response = last_message.content if isinstance(last_message, AIMessage) else str(last_message)
            else:
                ai_response = "I'm sorry, I had trouble processing that. Could you rephrase?"
            
            # Save messages to database (using existing MessageHistoryStore)
            message_store = MessageHistoryStore(db=db)
            chat_history = message_store.get_chat_history(session_id)
            chat_history.add_user_message(user_message)
            chat_history.add_ai_message(ai_response)
            
            # Save updated state
            await self.memory_manager.save_state(session_id, result, db)
            
            logger.info(f"Response generated successfully for session {session_id}")
            return ai_response
        
        except Exception as e:
            logger.error(f"Error in process_message: {e}", exc_info=True)
            return "I'm sorry, I encountered an error processing your message. Please try again."
    
    # ====================
    # STATE MACHINE NODES
    # ====================
    
    async def classify_intent_node(self, state: ConversationState) -> ConversationState:
        """Node: Classify user intent"""
        try:
            last_message = state["messages"][-1].content if state["messages"] else ""
            
            # Use semantic router for fast classification
            intent = self.intent_router.classify(last_message)
            
            logger.info(f"Classified intent: {intent}")
            
            # Store intent for routing
            state["_routing_intent"] = intent  # Temporary field for routing
            
            return state
        
        except Exception as e:
            logger.error(f"Error in classify_intent_node: {e}")
            state["_routing_intent"] = IntentTypes.UNCLEAR
            return state
    
    async def crisis_check_node(self, state: ConversationState) -> ConversationState:
        """Node: Handle crisis situation"""
        try:
            last_message = state["messages"][-1].content
            
            # Run ensemble crisis detection
            crisis_result = await self.llm_engine.detect_crisis_ensemble(last_message)
            
            state["is_crisis"] = crisis_result["is_crisis"]
            state["crisis_confidence"] = crisis_result["confidence"]
            
            if crisis_result["is_crisis"]:
                # Immediate crisis response
                state["messages"].append(AIMessage(content=CRISIS_RESPONSE_TEMPLATE))
                state["current_stage"] = ConversationStages.COMPLETED
                
                logger.warning(f"CRISIS DETECTED with confidence {crisis_result['confidence']}")
            
            return state
        
        except Exception as e:
            logger.error(f"Error in crisis_check_node: {e}")
            # Conservative: if error, provide crisis resources
            state["messages"].append(AIMessage(content=CRISIS_RESPONSE_TEMPLATE))
            return state
    
    async def greeting_node(self, state: ConversationState) -> ConversationState:
        """Node: Handle greeting and initial assessment"""
        try:
            last_message = state["messages"][-1].content
            
            # Analyze sentiment
            sentiment_prompt = SENTIMENT_ANALYSIS_PROMPT.format(message=last_message)
            sentiment = await self.llm_engine.generate(
                messages=[HumanMessage(content=sentiment_prompt)],
                task_type=TaskType.SENTIMENT_ANALYSIS,
            )
            
            state["sentiment"] = sentiment.strip().lower()
            
            # Generate greeting response based on sentiment
            if state["sentiment"] == "negative":
                # Use Claude for empathetic greeting
                system_msg = SystemMessage(content=BASE_SYSTEM_PROMPT)
                history_context = "\n".join([
                    f"{'User' if isinstance(msg, HumanMessage) else 'Assistant'}: {msg.content}"
                    for msg in state["messages"][-3:]
                ])
                
                greeting_prompt = f"""This is the start of a conversation. The user expressed: "{last_message}"

The sentiment is negative, showing distress. Provide a warm, empathetic greeting following these rules:
- Introduce yourself as Acutie ONCE
- Acknowledge their difficulty
- Ask for their name or preferred name
- Keep it natural and warm
- NO markdown symbols
- Be concise (2-3 sentences)

Your response:"""
                
                response = await self.llm_engine.generate(
                    messages=[system_msg, HumanMessage(content=greeting_prompt)],
                    task_type=TaskType.GREETING_EMPATHETIC,
                    use_cache=True,
                )
                
                state["needs_demographics"] = True
            
            else:
                # Use GPT-4o-mini for neutral/positive greeting
                system_msg = SystemMessage(content=BASE_SYSTEM_PROMPT)
                
                greeting_prompt = f"""This is the start of a conversation. The user said: "{last_message}"

Provide a brief professional greeting and ask your first assessment question:
- Introduce yourself as Acutie
- Skip demographics (neutral sentiment)
- Ask about duration: how long they've experienced this
- Be direct and clear
- NO markdown symbols

Your response:"""
                
                response = await self.llm_engine.generate(
                    messages=[system_msg, HumanMessage(content=greeting_prompt)],
                    task_type=TaskType.GREETING_NEUTRAL,
                )
                
                state["question_count"] = 1
                state["questions_asked"].append("duration")
            
            # Add AI response
            state["messages"].append(AIMessage(content=response))
            state["current_stage"] = ConversationStages.ASSESSMENT
            
            return state
        
        except Exception as e:
            logger.error(f"Error in greeting_node: {e}")
            fallback = "Hello, I'm Acutie, your mental health assessment assistant. How can I help you today?"
            state["messages"].append(AIMessage(content=fallback))
            return state
    
    async def assessment_node(self, state: ConversationState) -> ConversationState:
        """Node: Conduct assessment questions"""
        try:
            last_message = state["messages"][-1].content
            
            # Extract information from user's response
            extraction_prompt = RESPONSE_EXTRACTION_PROMPT.format(user_message=last_message)
            extracted_json = await self.llm_engine.generate(
                messages=[HumanMessage(content=extraction_prompt)],
                task_type=TaskType.RESPONSE_EXTRACTION,
            )
            
            # Parse and store extracted data
            try:
                extracted_data = json.loads(extracted_json)
                state["symptoms"].update(extracted_data)
            except json.JSONDecodeError:
                logger.warning("Could not parse extracted data as JSON")
            
            # Check if we have enough information for diagnosis
            question_count = state.get("question_count", 0)
            
            if question_count >= 5 and len(state["symptoms"]) >= 4:
                # Ready for diagnosis
                state["ready_for_diagnosis"] = True
                state["_routing_intent"] = "diagnosis"  # Route to diagnosis
                
                # Generate diagnosis
                return await self.diagnosis_node(state)
            
            else:
                # Generate next question using Claude (natural conversation)
                system_msg = SystemMessage(content=BASE_SYSTEM_PROMPT)
                
                recent_messages = "\n".join([
                    f"{'User' if isinstance(msg, HumanMessage) else 'Assistant'}: {msg.content}"
                    for msg in state["messages"][-6:]
                ])
                
                # Extract EXACT condition mentioned by user, not generic
                first_user_message = next((msg.content for msg in state["messages"] if isinstance(msg, HumanMessage)), "")
                
                # Detect specific conditions from first message
                detected_condition = "their concern"
                if "anxious" in first_user_message.lower() or "anxiety" in first_user_message.lower():
                    detected_condition = "anxiety"
                elif "depress" in first_user_message.lower() or "sad" in first_user_message.lower():
                    detected_condition = "depression"  
                elif "stress" in first_user_message.lower():
                    detected_condition = "stress"
                elif "trauma" in first_user_message.lower() or "ptsd" in first_user_message.lower():
                    detected_condition = "trauma"
                
                question_prompt = QUESTION_GENERATION_PROMPT.format(
                    detected_condition=detected_condition,
                    already_asked=", ".join(state["questions_asked"]),
                    recent_messages=recent_messages,
                )
                
                next_question = await self.llm_engine.generate(
                    messages=[system_msg, HumanMessage(content=question_prompt)],
                    task_type=TaskType.ASSESSMENT_QUESTION,
                    use_cache=True,
                )
                
                # Add AI response
                state["messages"].append(AIMessage(content=next_question))
                state["question_count"] += 1
                state["current_stage"] = ConversationStages.ASSESSMENT
            
            return state
        
        except Exception as e:
            logger.error(f"Error in assessment_node: {e}")
            fallback = "Could you tell me more about how this has been affecting you?"
            state["messages"].append(AIMessage(content=fallback))
            return state
    
    async def diagnosis_node(self, state: ConversationState) -> ConversationState:
        """Node: Generate diagnosis and assessment report"""
        try:
            # Prepare collected data
            assessment_data = {
                "symptoms": state["symptoms"],
                "question_count": state["question_count"],
                "questions_asked": state["questions_asked"],
                "sentiment": state["sentiment"],
            }
            
            # Step 1: Clinical analysis using GPT-5
            analysis_prompt = DIAGNOSIS_ANALYSIS_PROMPT.format(
                assessment_data=json.dumps(assessment_data, indent=2)
            )
            
            analysis_json = await self.llm_engine.generate(
                messages=[HumanMessage(content=analysis_prompt)],
                task_type=TaskType.DIAGNOSIS_ANALYSIS,
            )
            
            # Step 2: Format into natural language report using Claude
            formatting_prompt = DIAGNOSIS_FORMATTING_PROMPT.format(
                analysis_json=analysis_json
            )
            
            system_msg = SystemMessage(content=BASE_SYSTEM_PROMPT)
            formatted_report = await self.llm_engine.generate(
                messages=[system_msg, HumanMessage(content=formatting_prompt)],
                task_type=TaskType.DIAGNOSIS_FORMATTING,
                use_cache=True,
            )
            
            # Add diagnosis to messages
            state["messages"].append(AIMessage(content=formatted_report))
            state["current_stage"] = ConversationStages.COMPLETED
            
            logger.info("Diagnosis report generated successfully")
            return state
        
        except Exception as e:
            logger.error(f"Error in diagnosis_node: {e}")
            fallback = "Based on what you've shared, I recommend speaking with a mental health professional who can provide a proper assessment and support. This conversation has given me helpful information, but a licensed professional can offer you an official diagnosis and treatment plan."
            state["messages"].append(AIMessage(content=fallback))
            return state
    
    async def off_topic_node(self, state: ConversationState) -> ConversationState:
        """Node: Handle off-topic messages"""
        state["messages"].append(AIMessage(content=OFF_TOPIC_RESPONSE))
        return state
    
    # ====================
    # ROUTING LOGIC
    # ====================
    
    def route_by_intent(
        self, 
        state: ConversationState
    ) -> Literal["crisis", "greeting", "assessment", "diagnosis", "off_topic"]:
        """
        Route to next node based on classified intent and conversation stage
        """
        intent = state.get("_routing_intent", IntentTypes.UNCLEAR)
        current_stage = state.get("current_stage", ConversationStages.CLASSIFY_INTENT)
        question_count = state.get("question_count", 0)
        
        # Crisis always takes priority
        if intent == IntentTypes.CRISIS:
            return "crisis"
        
        # Off-topic
        if intent == IntentTypes.OFF_TOPIC:
            return "off_topic"
        
        # First message - go to greeting
        if intent == IntentTypes.FIRST_MESSAGE or question_count == 0:
            return "greeting"
        
        # Ready for diagnosis
        if state.get("ready_for_diagnosis") or question_count >= 5:
            return "diagnosis"
        
        # Assessment response or unclear - continue assessment
        if intent == IntentTypes.ASSESSMENT_RESPONSE or intent == IntentTypes.UNCLEAR:
            return "assessment"
        
        # Demographic response - continue to assessment
        if intent == IntentTypes.DEMOGRAPHIC_RESPONSE:
            return "assessment"
        
        # Default to assessment
        return "assessment"

