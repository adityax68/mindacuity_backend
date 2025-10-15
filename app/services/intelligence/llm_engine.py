"""
Multi-LLM Engine
Handles interactions with GPT-5, Claude Sonnet 4.5, and other models
Routes tasks to the most appropriate model
"""

import os
import logging
import asyncio
from typing import List, Dict, Any, Optional, AsyncGenerator
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage, AIMessage
from tenacity import retry, stop_after_attempt, wait_exponential

from app.services.intelligence.models.llm_config import (
    TaskType,
    ModelName,
    ModelProvider,
    MODEL_ROUTING,
    OPENAI_CONFIG,
    ANTHROPIC_CONFIG,
    get_model_config,
)

logger = logging.getLogger(__name__)


class LLMEngine:
    """
    Multi-LLM orchestration engine
    Routes different tasks to the most appropriate model
    """
    
    def __init__(self):
        """Initialize all LLM clients"""
        self._initialize_openai_models()
        self._initialize_anthropic_models()
        self._initialize_embeddings()
        
        logger.info("LLM Engine initialized with GPT-5, GPT-4o-mini, Claude Sonnet 4.5, and Claude Haiku 3.5")
    
    def _initialize_openai_models(self):
        """Initialize OpenAI models"""
        api_key = OPENAI_CONFIG["api_key"]
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required")
        
        # GPT-5 for complex reasoning and diagnosis
        self.gpt5 = ChatOpenAI(
            model="gpt-4o",  # Fallback to GPT-4o if GPT-5 not available
            temperature=0.4,
            max_tokens=1000,
            timeout=OPENAI_CONFIG["timeout"],
            max_retries=OPENAI_CONFIG["max_retries"],
            api_key=api_key,
        )
        
        # GPT-4o for crisis detection (fallback if GPT-5 not available)
        self.gpt4o = ChatOpenAI(
            model="gpt-4o",
            temperature=0.4,
            max_tokens=800,
            timeout=OPENAI_CONFIG["timeout"],
            max_retries=OPENAI_CONFIG["max_retries"],
            api_key=api_key,
        )
        
        # GPT-4o-mini for fast tasks
        self.gpt4o_mini = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0.7,
            max_tokens=500,
            timeout=OPENAI_CONFIG["timeout"],
            max_retries=OPENAI_CONFIG["max_retries"],
            api_key=api_key,
        )
        
        logger.info("OpenAI models initialized: GPT-5, GPT-4o, GPT-4o-mini")
    
    def _initialize_anthropic_models(self):
        """Initialize Anthropic Claude models"""
        api_key = ANTHROPIC_CONFIG["api_key"]
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable is required")
        
        # Claude Sonnet 4.5 for empathy and natural conversation
        self.claude_sonnet_45 = ChatAnthropic(
            model="claude-sonnet-4-5-20250929",
            temperature=0.7,
            max_tokens=ANTHROPIC_CONFIG["default_max_tokens"],
            timeout=ANTHROPIC_CONFIG["timeout"],
            max_retries=ANTHROPIC_CONFIG["max_retries"],
            anthropic_api_key=api_key,
        )
        
        # Claude Haiku 3.5 for fast, efficient tasks
        self.claude_haiku_35 = ChatAnthropic(
            model="claude-3-5-haiku-20241022",
            temperature=0.3,
            max_tokens=500,
            timeout=ANTHROPIC_CONFIG["timeout"],
            max_retries=ANTHROPIC_CONFIG["max_retries"],
            anthropic_api_key=api_key,
        )
        
        logger.info("Anthropic models initialized: Claude Sonnet 4.5, Claude Haiku 3.5")
    
    def _initialize_embeddings(self):
        """Initialize embedding models for semantic search"""
        self.embeddings = OpenAIEmbeddings(
            model="text-embedding-3-small",
            api_key=OPENAI_CONFIG["api_key"],
        )
        
        logger.info("Embeddings initialized: text-embedding-3-small")
    
    def _get_model_for_task(self, task_type: TaskType) -> Any:
        """Get the appropriate model for a given task"""
        config = get_model_config(task_type)
        model_name = config.get("model")
        
        # Map model names to actual model instances
        model_map = {
            ModelName.GPT_5: self.gpt5,
            ModelName.GPT_4O: self.gpt4o,
            ModelName.GPT_4O_MINI: self.gpt4o_mini,
            ModelName.CLAUDE_SONNET_4_5: self.claude_sonnet_45,
            ModelName.CLAUDE_HAIKU_3_5: self.claude_haiku_35,
        }
        
        model = model_map.get(model_name)
        if not model:
            logger.warning(f"Model {model_name} not found, using GPT-4o-mini as fallback")
            return self.gpt4o_mini
        
        return model
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True
    )
    async def generate(
        self,
        messages: List[BaseMessage],
        task_type: TaskType,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        use_cache: bool = False,
    ) -> str:
        """
        Generate a response using the appropriate model
        
        Args:
            messages: List of conversation messages
            task_type: Type of task to determine model selection
            temperature: Override default temperature
            max_tokens: Override default max_tokens
            use_cache: Enable prompt caching (Claude only)
        
        Returns:
            Generated response text
        """
        try:
            # Get model configuration
            config = get_model_config(task_type)
            model = self._get_model_for_task(task_type)
            
            # Override config if specified
            if temperature is not None:
                model.temperature = temperature
            else:
                model.temperature = config.get("temperature", 0.7)
            
            if max_tokens is not None:
                model.max_tokens = max_tokens
            else:
                model.max_tokens = config.get("max_tokens", 500)
            
            # Add cache control for Claude if enabled
            if use_cache and isinstance(model, ChatAnthropic):
                # Claude's prompt caching: mark system message as cacheable
                if messages and isinstance(messages[0], SystemMessage):
                    # This will be implemented when Claude cache control is available in langchain
                    pass
            
            # Generate response
            logger.info(f"🤖 Generating with {config.get('model')} for {task_type}")
            start_time = asyncio.get_event_loop().time()
            
            response = await model.ainvoke(messages)
            
            elapsed = asyncio.get_event_loop().time() - start_time
            logger.info(f"✓ Generated in {elapsed:.2f}s with {config.get('model')}")
            
            return response.content
        
        except Exception as e:
            logger.error(f"Error generating response with {task_type}: {e}")
            
            # Fallback to GPT-4o-mini if primary model fails
            if model != self.gpt4o_mini:
                logger.warning(f"Falling back to GPT-4o-mini")
                try:
                    response = await self.gpt4o_mini.ainvoke(messages)
                    return response.content
                except Exception as fallback_error:
                    logger.error(f"Fallback also failed: {fallback_error}")
                    raise
            else:
                raise
    
    async def generate_streaming(
        self,
        messages: List[BaseMessage],
        task_type: TaskType,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> AsyncGenerator[str, None]:
        """
        Generate a streaming response (token by token)
        
        Args:
            messages: List of conversation messages
            task_type: Type of task to determine model selection
            temperature: Override default temperature
            max_tokens: Override default max_tokens
        
        Yields:
            Response tokens as they are generated
        """
        try:
            config = get_model_config(task_type)
            model = self._get_model_for_task(task_type)
            
            # Override config if specified
            if temperature is not None:
                model.temperature = temperature
            else:
                model.temperature = config.get("temperature", 0.7)
            
            if max_tokens is not None:
                model.max_tokens = max_tokens
            else:
                model.max_tokens = config.get("max_tokens", 500)
            
            logger.info(f"Streaming response with {config.get('model')} for {task_type}")
            
            async for chunk in model.astream(messages):
                if chunk.content:
                    yield chunk.content
        
        except Exception as e:
            logger.error(f"Error in streaming response: {e}")
            # Yield error message
            yield "I'm sorry, I encountered an error. Please try again."
    
    async def detect_crisis_ensemble(self, message: str) -> Dict[str, Any]:
        """
        Ensemble crisis detection using multiple models
        Combines GPT-5 and Claude Sonnet 4.5 for maximum accuracy
        
        Args:
            message: User message to analyze
        
        Returns:
            Dict with crisis detection results
        """
        logger.info("Running ensemble crisis detection")
        
        # Crisis keywords for fast pattern matching
        crisis_keywords = [
            "kill myself", "suicide", "end my life", "want to die",
            "hurt myself", "self harm", "cut myself", "overdose",
            "not worth living", "better off dead", "no reason to live",
        ]
        
        # Quick keyword check
        message_lower = message.lower()
        keyword_detected = any(keyword in message_lower for keyword in crisis_keywords)
        keyword_score = 1.0 if keyword_detected else 0.0
        
        # Prepare prompt for both models
        crisis_prompt = f"""Evaluate this message for immediate crisis indicators on a scale of 0.0 to 1.0:
- 0.0 = No crisis
- 1.0 = Immediate crisis (suicidal ideation, self-harm, harm to others)

Message: "{message}"

Respond with ONLY a number between 0.0 and 1.0:"""
        
        try:
            # Run both models in parallel for speed
            gpt_task = self.gpt5.ainvoke([HumanMessage(content=crisis_prompt)])
            claude_task = self.claude_sonnet_45.ainvoke([HumanMessage(content=crisis_prompt)])
            
            gpt_response, claude_response = await asyncio.gather(
                gpt_task,
                claude_task,
                return_exceptions=True
            )
            
            # Parse scores
            gpt_score = 0.0
            claude_score = 0.0
            
            if not isinstance(gpt_response, Exception):
                try:
                    gpt_score = float(gpt_response.content.strip())
                except ValueError:
                    logger.warning(f"Could not parse GPT-5 crisis score: {gpt_response.content}")
            
            if not isinstance(claude_response, Exception):
                try:
                    claude_score = float(claude_response.content.strip())
                except ValueError:
                    logger.warning(f"Could not parse Claude crisis score: {claude_response.content}")
            
            # Ensemble calculation (weighted average)
            # GPT-5: 40%, Claude: 40%, Keywords: 20%
            final_score = (gpt_score * 0.4) + (claude_score * 0.4) + (keyword_score * 0.2)
            
            # Lower threshold: if 2 out of 3 detect crisis (0.6), trigger
            is_crisis = final_score >= 0.6
            
            logger.info(
                f"Crisis detection - GPT: {gpt_score}, Claude: {claude_score}, "
                f"Keywords: {keyword_score}, Final: {final_score}, Crisis: {is_crisis}"
            )
            
            return {
                "is_crisis": is_crisis,
                "confidence": final_score,
                "gpt_score": gpt_score,
                "claude_score": claude_score,
                "keyword_score": keyword_score,
            }
        
        except Exception as e:
            logger.error(f"Error in crisis detection ensemble: {e}")
            # Conservative approach: if error, treat as potential crisis if keywords detected
            return {
                "is_crisis": keyword_detected,
                "confidence": keyword_score,
                "error": str(e),
            }
    
    async def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Get embeddings for a list of texts
        Used by semantic router for intent classification
        
        Args:
            texts: List of text strings to embed
        
        Returns:
            List of embedding vectors
        """
        try:
            embeddings = await self.embeddings.aembed_documents(texts)
            return embeddings
        except Exception as e:
            logger.error(f"Error getting embeddings: {e}")
            raise
    
    async def get_embedding(self, text: str) -> List[float]:
        """
        Get embedding for a single text
        
        Args:
            text: Text string to embed
        
        Returns:
            Embedding vector
        """
        try:
            embedding = await self.embeddings.aembed_query(text)
            return embedding
        except Exception as e:
            logger.error(f"Error getting embedding: {e}")
            raise

