"""
Pydantic models and JSON Schema definitions for RPGAI.
Contains the structured output schema for Gemini and data models for API contracts.
"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator
from enum import Enum


# ============================================================================
# ENUMS
# ============================================================================

class Emotion(str, Enum):
    """NPC emotional states."""
    NEUTRAL = "neutral"
    HAPPY = "happy"
    ANGRY = "angry"
    FEAR = "fear"
    SAD = "sad"
    SURPRISED = "surprised"
    DISGUST = "disgust"


class StyleTag(str, Enum):
    """Speech style modifiers."""
    FORMAL = "formal"
    CASUAL = "casual"
    WHISPER = "whisper"
    SHOUT = "shout"
    MYSTICAL = "mystical"
    GUARDED = "guarded"
    TEASING = "teasing"
    URGENT = "urgent"


class BehaviorDirective(str, Enum):
    """Actions the NPC should take."""
    NONE = "none"
    APPROACH = "approach"
    STEP_BACK = "step_back"
    FLEE = "flee"
    ATTACK = "attack"
    CALL_GUARD = "call_guard"
    GIVE_ITEM = "give_item"
    START_QUEST = "start_quest"
    OPEN_SHOP = "open_shop"
    HEAL_PLAYER = "heal_player"


class SSMLStyle(str, Enum):
    """SSML speech styles."""
    DEFAULT = "default"
    NARRATION = "narration"
    WHISPERED = "whispered"
    SHOUTED = "shouted"
    URGENT = "urgent"
    CALM = "calm"


# ============================================================================
# GEMINI JSON SCHEMA (for structured output)
# ============================================================================

NPC_DIALOGUE_SCHEMA = {
    "type": "object",
    "required": ["utterance", "emotion", "behavior_directive"],
    "properties": {
        "utterance": {
            "type": "string",
            "maxLength": 320,
            "description": "The NPC's spoken response (1-3 sentences)"
        },
        "emotion": {
            "type": "string",
            "enum": ["neutral", "happy", "angry", "fear", "sad", "surprised", "disgust"],
            "description": "Current emotional state"
        },
        "style_tags": {
            "type": "array",
            "maxItems": 3,
            "items": {
                "type": "string",
                "enum": ["formal", "casual", "whisper", "shout", "mystical", "guarded", "teasing", "urgent"]
            },
            "description": "Speech style modifiers"
        },
        "behavior_directive": {
            "type": "string",
            "enum": ["none", "approach", "step_back", "flee", "attack", "call_guard", 
                    "give_item", "start_quest", "open_shop", "heal_player"],
            "description": "Action the NPC should perform"
        },
        "memory_writes": {
            "type": "array",
            "maxItems": 2,
            "items": {
                "type": "object",
                "required": ["salience", "text"],
                "properties": {
                    "salience": {
                        "type": "integer",
                        "minimum": 0,
                        "maximum": 3,
                        "description": "Memory importance (0=trivial, 3=critical)"
                    },
                    "text": {
                        "type": "string",
                        "maxLength": 160,
                        "description": "What to remember"
                    },
                    "keys": {
                        "type": "array",
                        "maxItems": 4,
                        "items": {"type": "string"},
                        "description": "Search keywords"
                    },
                    "private": {
                        "type": "boolean",
                        "default": True,
                        "description": "Whether only this NPC knows this"
                    }
                }
            },
            "description": "Notable events to store in memory"
        },
        "public_events": {
            "type": "array",
            "maxItems": 1,
            "items": {
                "type": "object",
                "required": ["event_type"],
                "properties": {
                    "event_type": {
                        "type": "string",
                        "description": "Type of world event (e.g., 'crime_witnessed')"
                    },
                    "payload": {
                        "type": "object",
                        "description": "Event-specific data"
                    }
                }
            },
            "description": "Events visible to other NPCs"
        },
        "voice_hint": {
            "type": "object",
            "properties": {
                "voice_preset": {
                    "type": "string",
                    "description": "Voice character name"
                },
                "ssml_style": {
                    "type": "string",
                    "enum": ["default", "narration", "whispered", "shouted", "urgent", "calm"],
                    "description": "SSML rendering style"
                }
            },
            "description": "TTS voice configuration hints"
        }
    },
    "additionalProperties": False
}


# ============================================================================
# PYDANTIC MODELS (for API validation)
# ============================================================================

class MemoryWrite(BaseModel):
    """A memory entry to be written."""
    salience: int = Field(ge=0, le=3, description="Importance level (0-3)")
    text: str = Field(max_length=160, description="Memory content")
    keys: Optional[List[str]] = Field(default=None, max_length=4)
    private: bool = Field(default=True)


class PublicEvent(BaseModel):
    """A world event visible to multiple NPCs."""
    event_type: str
    payload: Optional[Dict[str, Any]] = None


class VoiceHint(BaseModel):
    """TTS voice configuration."""
    voice_preset: Optional[str] = None
    ssml_style: Optional[SSMLStyle] = SSMLStyle.DEFAULT


class NpcDialogueResponse(BaseModel):
    """
    Structured response from Gemini matching NPC_DIALOGUE_SCHEMA.
    This is the validated output Unity will receive.
    """
    utterance: str = Field(max_length=320)
    emotion: Emotion
    style_tags: Optional[List[StyleTag]] = Field(default=None, max_length=3)
    behavior_directive: BehaviorDirective
    memory_writes: Optional[List[MemoryWrite]] = Field(default=None, max_length=2)
    public_events: Optional[List[PublicEvent]] = Field(default=None, max_length=1)
    voice_hint: Optional[VoiceHint] = None


class Persona(BaseModel):
    """NPC personality definition."""
    name: str
    role: str = Field(description="Race/occupation (e.g., 'Elven mage')")
    values: List[str] = Field(description="Core values (e.g., ['order', 'wisdom'])")
    quirks: List[str] = Field(description="Personality traits")
    backstory: List[str] = Field(description="Key background hooks")


class GameContext(BaseModel):
    """Current game state context."""
    scene: str = Field(description="Location name")
    time_of_day: str = Field(description="e.g., 'dusk', 'noon'")
    weather: str = Field(description="e.g., 'light_rain', 'clear'")
    last_player_action: Optional[str] = None
    player_reputation: int = Field(default=0, ge=-10, le=20)
    npc_health: int = Field(default=100, ge=0, le=100)
    npc_alertness: float = Field(default=0.0, ge=0.0, le=1.0)


class ChatTurnRequest(BaseModel):
    """WebSocket payload from Unity for a single dialogue turn."""
    npc_id: str
    player_id: str
    player_text: str = Field(description="What the player said")
    persona: Persona
    context: GameContext


class NpcMemoryWrite(BaseModel):
    """HTTP POST request to write a memory."""
    npc_id: str
    player_id: str
    text: str = Field(max_length=160)
    salience: int = Field(ge=0, le=3)
    keys: Optional[List[str]] = Field(default=None, max_length=4)
    private: bool = True


class MemoryEntry(BaseModel):
    """A retrieved memory entry."""
    id: int
    npc_id: str
    player_id: str
    text: str
    salience: int
    private: bool
    keys: Optional[str] = None  # stored as JSON string in DB
    ts: int  # Unix timestamp


class TTSRequest(BaseModel):
    """TTS synthesis request."""
    ssml: str = Field(description="SSML-formatted text")
    voice_name: str = Field(default="en-US-Neural2-C")


class TTSResponse(BaseModel):
    """TTS synthesis response."""
    audio_url: str


# ============================================================================
# SYSTEM INSTRUCTION (for Gemini)
# ============================================================================

SYSTEM_INSTRUCTION = """You are the Dialogue Brain for an in-world NPC in a medieval-fantasy RPG.

HARD RULES:
- Stay strictly in-lore. Never mention models, prompts, APIs, or the player's real world.
- Be concise: 1–3 sentences. Max 320 chars of spoken text.
- Use CURRENT CONTEXT only if relevant; never invent events.
- Safety: avoid slurs, sexual content, self-harm advice.
- OUTPUT ONLY valid JSON that matches the provided JSON Schema. No extra text.

PERSONALITY ADAPTATION:
- Match the persona's values, quirks, and backstory.
- Let emotion guide word choice (angry → curt; happy → warm).
- Use retrieved memories to maintain continuity.

ACTION LOGIC:
- reputation < 0: be guarded or hostile.
- reputation > 10: be helpful and warm.
- Wrongdoing → 'call_guard' or 'step_back'.
- Kindness → 'open_shop' or 'give_item'.

MEMORY:
- Write at most 1 memory_writes entry per turn.
- Only record notable interactions (salience ≥ 1).
"""

