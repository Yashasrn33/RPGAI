"""
Gemini LLM client for NPC dialogue generation.
Implements structured JSON output with streaming support.
"""
import json
import logging
from typing import AsyncGenerator, Dict, Any, List
from google import genai
from google.genai import types

from schemas import (
    NPC_DIALOGUE_SCHEMA,
    SYSTEM_INSTRUCTION,
    ChatTurnRequest,
    NpcDialogueResponse,
    MemoryEntry
)
from settings import settings

logger = logging.getLogger(__name__)


class GeminiClient:
    """
    Gemini API client configured for structured NPC dialogue generation.
    Enforces JSON Schema output and streams tokens to WebSocket clients.
    """
    
    def __init__(self):
        """Initialize the Gemini client with API key from settings."""
        if not settings.gemini_api_key:
            raise ValueError("GEMINI_API_KEY not configured")
        
        self.client = genai.Client(api_key=settings.gemini_api_key)
        self.model = settings.gemini_model
        logger.info(f"GeminiClient initialized with model: {self.model}")
    
    def _build_turn_content(
        self,
        payload: ChatTurnRequest,
        memories: List[MemoryEntry]
    ) -> str:
        """
        Build the user content string from persona, context, memories, and player input.
        
        Args:
            payload: The chat turn request from Unity
            memories: Retrieved memories for context
        
        Returns:
            Formatted prompt string
        """
        persona = payload.persona
        ctx = payload.context
        
        # Build memory section
        memory_lines = []
        for mem in memories:
            memory_lines.append(f"- (salience {mem.salience}) {mem.text}")
        memory_section = "\n".join(memory_lines) if memory_lines else "- (No prior memories)"
        
        # Format the turn using the template
        content = f"""[PERSONA]
Name: {persona.name}
Role: {persona.role}
Values: {", ".join(persona.values)}
Quirks: {", ".join(persona.quirks)}
Backstory hooks: {"; ".join(persona.backstory)}

[CONTEXT]
scene={ctx.scene}  time_of_day={ctx.time_of_day}  weather={ctx.weather}
last_player_action={ctx.last_player_action or "none"}
player_reputation={ctx.player_reputation} (-10..+20)
npc_health={ctx.npc_health}  npc_alertness={ctx.npc_alertness}

[RETRIEVED_MEMORY]
{memory_section}

[PLAYER_TEXT]
"{payload.player_text}"

[STYLE & ACTION HINTS]
- Choose a fitting emotion that matches the subtext.
- If reputation < 0: guarded/hostile tone; if > 10: warm/helpful tone.
- Map severe wrongdoing to 'call_guard' or 'step_back'; kindness to 'open_shop' or 'give_item'.
- Write at most 1 memory_writes entry if something notable happened.
- voice_hint: choose calm, context-appropriate voice unless situation suggests otherwise.
"""
        return content
    
    async def generate_npc_response_stream(
        self,
        payload: ChatTurnRequest,
        memories: List[MemoryEntry]
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Generate NPC response with token streaming and final validated JSON.
        
        This is the main entry point called by the WebSocket endpoint.
        Streams intermediate tokens, then yields a final validated response.
        
        Args:
            payload: The chat turn request from Unity
            memories: Retrieved memories for context
        
        Yields:
            Dicts in format:
            - {"type": "token", "text": "..."} for intermediate tokens
            - {"type": "final", "json": "{...}"} for the validated final response
        """
        try:
            # Build the turn content
            turn_content = self._build_turn_content(payload, memories)
            
            # Configure generation with structured output
            config = types.GenerateContentConfig(
                system_instruction=SYSTEM_INSTRUCTION,
                response_mime_type="application/json",
                response_schema=NPC_DIALOGUE_SCHEMA,  # Enforce schema
                temperature=settings.temperature,
                top_p=settings.top_p,
                max_output_tokens=settings.max_output_tokens
            )
            
            logger.info(f"Generating response for npc={payload.npc_id}, player={payload.player_id}")
            
            # Stream the response
            accumulated_text = ""
            
            response = self.client.models.generate_content(
                model=self.model,
                contents=turn_content,
                config=config
            )
            
            # For non-streaming, we get the full text at once
            # Since Gemini structured output doesn't support true streaming yet,
            # we'll simulate it by yielding chunks
            full_text = response.text
            accumulated_text = full_text
            
            # Yield the complete response as tokens (chunked for streaming effect)
            chunk_size = 20
            for i in range(0, len(full_text), chunk_size):
                chunk = full_text[i:i + chunk_size]
                yield {"type": "token", "text": chunk}
            
            # Validate the final JSON
            try:
                parsed_json = json.loads(accumulated_text)
                validated_response = NpcDialogueResponse(**parsed_json)
                
                # Yield the final validated JSON
                yield {
                    "type": "final",
                    "json": validated_response.model_dump_json()
                }
                
                logger.info(
                    f"Response generated: emotion={validated_response.emotion}, "
                    f"behavior={validated_response.behavior_directive}, "
                    f"utterance_len={len(validated_response.utterance)}"
                )
                
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON from model: {e}")
                # Fallback response
                fallback = {
                    "utterance": "I... seem to have lost my words.",
                    "emotion": "neutral",
                    "behavior_directive": "none"
                }
                yield {"type": "final", "json": json.dumps(fallback)}
                
            except Exception as e:
                logger.error(f"Validation error: {e}")
                # Fallback response
                fallback = {
                    "utterance": "Forgive me, I'm not feeling quite myself.",
                    "emotion": "neutral",
                    "behavior_directive": "none"
                }
                yield {"type": "final", "json": json.dumps(fallback)}
        
        except Exception as e:
            logger.error(f"Error generating response: {e}", exc_info=True)
            # Yield error as final response
            error_response = {
                "utterance": "I... I cannot speak right now.",
                "emotion": "neutral",
                "behavior_directive": "none"
            }
            yield {"type": "final", "json": json.dumps(error_response)}
    
    def generate_npc_response_sync(
        self,
        payload: ChatTurnRequest,
        memories: List[MemoryEntry]
    ) -> NpcDialogueResponse:
        """
        Synchronous version for testing or non-streaming use cases.
        
        Args:
            payload: The chat turn request
            memories: Retrieved memories for context
        
        Returns:
            Validated NpcDialogueResponse
        """
        turn_content = self._build_turn_content(payload, memories)
        
        config = types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION,
            response_mime_type="application/json",
            response_schema=NPC_DIALOGUE_SCHEMA,
            temperature=settings.temperature,
            top_p=settings.top_p,
            max_output_tokens=settings.max_output_tokens
        )
        
        response = self.client.models.generate_content(
            model=self.model,
            contents=turn_content,
            config=config
        )
        
        parsed_json = json.loads(response.text)
        return NpcDialogueResponse(**parsed_json)


# Global client instance
gemini_client = GeminiClient()


async def generate_npc_json_stream(
    payload: ChatTurnRequest,
    memories: List[MemoryEntry]
) -> AsyncGenerator[Dict[str, Any], None]:
    """
    Convenience function for generating NPC responses.
    This is what the FastAPI WebSocket endpoint calls.
    
    Args:
        payload: The chat turn request from Unity
        memories: Retrieved memories for context
    
    Yields:
        Stream of response chunks
    """
    async for chunk in gemini_client.generate_npc_response_stream(payload, memories):
        yield chunk

