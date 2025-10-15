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
            
            # CRITICAL: Quick keyword-based crisis check first (fast, no API calls)
            crisis_keywords = [
                "kill myself", "suicide", "end my life", "want to die",
                "hurt myself", "self harm", "cut myself", "overdose",
                "not worth living", "better off dead", "no reason to live",
            ]
            message_lower = user_message.lower()
            has_crisis_keywords = any(keyword in message_lower for keyword in crisis_keywords)
            
            # Only run expensive ensemble detection if keywords detected
            if has_crisis_keywords:
                logger.warning(f"Crisis keywords detected for session {session_id}, running full ensemble check")
                crisis_result = await self.llm_engine.detect_crisis_ensemble(user_message)
                
                if crisis_result["is_crisis"]:
                    logger.warning(f"CRISIS CONFIRMED for session {session_id}: confidence={crisis_result['confidence']}")
                    
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
            last_message = state["messages"][-1].content.lower()
            
            # Check if this is just a greeting (hi, hello, hey, etc.)
            simple_greetings = ["hi", "hello", "hey", "yo", "greetings", "good morning", "good evening", "good afternoon"]
            is_simple_greeting = any(greeting in last_message for greeting in simple_greetings) and len(last_message.split()) <= 3
            
            # If it's just a simple greeting, respond and ask what they're struggling with
            if is_simple_greeting:
                response = "Hello! I'm Acutie, your mental health assessment assistant. What are you currently struggling with—anxiety, low mood, stress, sleep problems, or something else?"
                state["messages"].append(AIMessage(content=response))
                state["current_stage"] = ConversationStages.ASSESSMENT
                return state
            
            # Otherwise, user has already mentioned a concern - proceed with sentiment analysis
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
                
                greeting_prompt = f"""The user shared their concern: "{last_message}"

The sentiment is negative, showing distress. Provide a warm, empathetic response following these rules:
- Introduce yourself as Acutie briefly if needed
- Acknowledge their difficulty with empathy
- Ask your first assessment question: How long have you been experiencing these feelings? Days, weeks, or months?
- Keep it natural and warm
- NO markdown symbols
- Be concise (2-3 sentences)

Your response:"""
                
                response = await self.llm_engine.generate(
                    messages=[system_msg, HumanMessage(content=greeting_prompt)],
                    task_type=TaskType.GREETING_EMPATHETIC,
                    use_cache=True,
                )
                
                state["needs_demographics"] = False  # Skip demographics for now
                state["question_count"] = 1
                state["questions_asked"].append("duration")
            
            else:
                # Use GPT-4o-mini for neutral/positive greeting
                system_msg = SystemMessage(content=BASE_SYSTEM_PROMPT)
                
                greeting_prompt = f"""The user mentioned: "{last_message}"

Provide a brief professional response and ask your first assessment question:
- Introduce yourself as Acutie briefly
- Ask about duration: How long have you been experiencing these feelings? Days, weeks, or months?
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
            fallback = "Hello, I'm Acutie, your mental health assessment assistant. What are you currently struggling with?"
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
                logger.info(f"Extracted symptoms: {extracted_data}")
            except json.JSONDecodeError:
                logger.warning(f"Could not parse extracted data as JSON: {extracted_json}")
            
            # Check if we have enough information for diagnosis
            question_count = state.get("question_count", 0)
            logger.info(f"Assessment progress: {question_count} questions asked, {len(state['symptoms'])} symptoms collected")
            
            # Trigger diagnosis after 6-7 questions OR if we have comprehensive data
            should_diagnose = (
                question_count >= 6 or  # After 6 questions minimum
                (question_count >= 5 and len(state["symptoms"]) >= 5)  # Or 5 questions with good data
            )
            
            if should_diagnose:
                logger.info("Sufficient data collected, generating diagnosis")
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
                
                # Extract EXACT condition mentioned by user from ALL their messages
                all_user_messages = " ".join([msg.content for msg in state["messages"] if isinstance(msg, HumanMessage)])
                
                # Detect specific conditions from all user messages
                detected_condition = "their concern"
                lower_messages = all_user_messages.lower()
                if "angry" in lower_messages or "anger" in lower_messages or "irritat" in lower_messages:
                    detected_condition = "anger and irritability"
                elif "anxious" in lower_messages or "anxiety" in lower_messages:
                    detected_condition = "anxiety"
                elif "depress" in lower_messages or "sad" in lower_messages:
                    detected_condition = "depression"  
                elif "stress" in lower_messages:
                    detected_condition = "stress"
                elif "trauma" in lower_messages or "ptsd" in lower_messages:
                    detected_condition = "trauma"
                
                # Determine next question topic based on what's already asked
                asked = set(state["questions_asked"])
                next_topic = None
                if "frequency" not in asked:
                    next_topic = "frequency"
                    state["questions_asked"].append("frequency")
                elif "intensity" not in asked:
                    next_topic = "intensity"
                    state["questions_asked"].append("intensity")
                elif "triggers" not in asked:
                    next_topic = "triggers"
                    state["questions_asked"].append("triggers")
                elif "impact" not in asked:
                    next_topic = "impact"
                    state["questions_asked"].append("impact")
                elif "physical_symptoms" not in asked:
                    next_topic = "physical_symptoms"
                    state["questions_asked"].append("physical_symptoms")
                elif "coping" not in asked:
                    next_topic = "coping"
                    state["questions_asked"].append("coping")
                
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
                
                logger.info(f"Generated question #{state['question_count']}, topic: {next_topic}")
            
            return state
        
        except Exception as e:
            logger.error(f"Error in assessment_node: {e}", exc_info=True)
            fallback = "Could you tell me more about how this has been affecting you?"
            state["messages"].append(AIMessage(content=fallback))
            return state
    
    async def diagnosis_node(self, state: ConversationState) -> ConversationState:
        """Node: Generate diagnosis and assessment report"""
        try:
            # Prepare collected data with ALL user messages for comprehensive analysis
            all_user_messages = [msg.content for msg in state["messages"] if isinstance(msg, HumanMessage)]
            conversation_transcript = "\n".join([
                f"{'User' if isinstance(msg, HumanMessage) else 'Assistant'}: {msg.content}"
                for msg in state["messages"]
            ])
            
            assessment_data = {
                "symptoms": state["symptoms"],
                "question_count": state["question_count"],
                "questions_asked": state["questions_asked"],
                "sentiment": state["sentiment"],
                "all_user_responses": all_user_messages,
                "conversation_transcript": conversation_transcript
            }
            
            logger.info(f"Generating diagnosis with data: {len(all_user_messages)} user messages, {len(state['symptoms'])} symptoms")
            
            # Step 1: Clinical analysis using GPT-5
            analysis_prompt = f"""{DIAGNOSIS_ANALYSIS_PROMPT.format(assessment_data=json.dumps(assessment_data, indent=2))}

IMPORTANT: 
- Identify SPECIFIC conditions mentioned by the user (e.g., anger issues, irritability, anxiety, depression)
- Provide SEVERITY LEVEL for each condition: MILD, MODERATE, or SEVERE
- Base severity on: frequency (daily vs weekly), intensity (1-10 scale), duration, and functional impact
- Include specific examples from their responses in the rationale"""
            
            analysis_json = await self.llm_engine.generate(
                messages=[HumanMessage(content=analysis_prompt)],
                task_type=TaskType.DIAGNOSIS_ANALYSIS,
            )
            
            logger.info(f"GPT-5 analysis: {analysis_json}")
            
            # Step 2: Format into natural language report using Claude
            formatting_prompt = f"""{DIAGNOSIS_FORMATTING_PROMPT.format(analysis_json=analysis_json)}

CRITICAL REQUIREMENTS:
- Use plain text only (NO markdown, NO asterisks, NO hashtags)
- Include SPECIFIC conditions identified (not generic)
- State clear SEVERITY LEVEL for each condition: MILD, MODERATE, or SEVERE
- Explain the severity rating based on their responses
- Include empathy and understanding in the tone
- End with appropriate recommendation based on severity
- Use section headers in CAPS with line breaks for structure"""
            
            system_msg = SystemMessage(content=BASE_SYSTEM_PROMPT)
            formatted_report = await self.llm_engine.generate(
                messages=[system_msg, HumanMessage(content=formatting_prompt)],
                task_type=TaskType.DIAGNOSIS_FORMATTING,
                use_cache=True,
            )
            
            logger.info(f"Claude formatted report: {formatted_report[:200]}...")
            
            # Add diagnosis to messages
            state["messages"].append(AIMessage(content=formatted_report))
            state["current_stage"] = ConversationStages.COMPLETED
            
            logger.info("Diagnosis report generated successfully")
            return state
        
        except Exception as e:
            logger.error(f"Error in diagnosis_node: {e}", exc_info=True)
            
            # Provide a more helpful fallback based on what we know
            detected_issue = "your concerns"
            all_messages = " ".join([msg.content for msg in state["messages"] if isinstance(msg, HumanMessage)])
            if "angry" in all_messages.lower() or "irritat" in all_messages.lower():
                detected_issue = "anger and irritability issues"
            elif "anxi" in all_messages.lower():
                detected_issue = "anxiety"
            elif "depress" in all_messages.lower():
                detected_issue = "depression"
            
            fallback = f"""Based on what you've shared about {detected_issue}, I recommend speaking with a mental health professional who can provide a proper assessment and support.

While I've gathered helpful information from our conversation, a licensed mental health professional can:
- Provide an official diagnosis
- Create a personalized treatment plan
- Offer ongoing support and therapy

Your wellbeing is important, and professional help can make a significant difference."""
            
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

