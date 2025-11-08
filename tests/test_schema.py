"""
Unit tests for schema validation.
Tests that sample Gemini outputs conform to the JSON Schema and Pydantic models.
"""
import pytest
import json
from pydantic import ValidationError

from server.schemas import (
    NpcDialogueResponse,
    Emotion,
    BehaviorDirective,
    StyleTag,
    MemoryWrite,
    Persona,
    GameContext,
    ChatTurnRequest,
    NPC_DIALOGUE_SCHEMA
)


def test_valid_minimal_response():
    """Test a minimal valid NPC response."""
    data = {
        "utterance": "Greetings, traveler.",
        "emotion": "neutral",
        "behavior_directive": "none"
    }
    
    response = NpcDialogueResponse(**data)
    assert response.utterance == "Greetings, traveler."
    assert response.emotion == Emotion.NEUTRAL
    assert response.behavior_directive == BehaviorDirective.NONE


def test_valid_full_response():
    """Test a complete NPC response with all fields."""
    data = {
        "utterance": "I remember you! You returned my lost ring. How may I help you today?",
        "emotion": "happy",
        "style_tags": ["formal", "warm"],
        "behavior_directive": "approach",
        "memory_writes": [
            {
                "salience": 2,
                "text": "Player asked about spell training",
                "keys": ["magic", "training"],
                "private": True
            }
        ],
        "public_events": [
            {
                "event_type": "quest_started",
                "payload": {"quest_id": "mage_apprentice"}
            }
        ],
        "voice_hint": {
            "voice_preset": "feminine_calm",
            "ssml_style": "calm"
        }
    }
    
    response = NpcDialogueResponse(**data)
    assert response.utterance == "I remember you! You returned my lost ring. How may I help you today?"
    assert response.emotion == Emotion.HAPPY
    assert len(response.style_tags) == 2
    assert response.behavior_directive == BehaviorDirective.APPROACH
    assert len(response.memory_writes) == 1
    assert response.memory_writes[0].salience == 2


def test_utterance_max_length():
    """Test that utterances longer than 320 chars are rejected."""
    data = {
        "utterance": "A" * 321,  # Too long
        "emotion": "neutral",
        "behavior_directive": "none"
    }
    
    with pytest.raises(ValidationError) as exc_info:
        NpcDialogueResponse(**data)
    
    assert "utterance" in str(exc_info.value)


def test_invalid_emotion():
    """Test that invalid emotion values are rejected."""
    data = {
        "utterance": "Hello",
        "emotion": "excited",  # Not in enum
        "behavior_directive": "none"
    }
    
    with pytest.raises(ValidationError):
        NpcDialogueResponse(**data)


def test_invalid_behavior_directive():
    """Test that invalid behavior directives are rejected."""
    data = {
        "utterance": "Hello",
        "emotion": "neutral",
        "behavior_directive": "dance"  # Not in enum
    }
    
    with pytest.raises(ValidationError):
        NpcDialogueResponse(**data)


def test_memory_write_validation():
    """Test memory write field validation."""
    # Valid memory write
    mem = MemoryWrite(
        salience=2,
        text="Player was kind",
        keys=["kindness"],
        private=True
    )
    assert mem.salience == 2
    
    # Invalid: salience out of range
    with pytest.raises(ValidationError):
        MemoryWrite(salience=5, text="Invalid")
    
    # Invalid: text too long
    with pytest.raises(ValidationError):
        MemoryWrite(salience=1, text="A" * 161)


def test_memory_writes_max_items():
    """Test that at most 2 memory writes are allowed."""
    data = {
        "utterance": "Hello",
        "emotion": "neutral",
        "behavior_directive": "none",
        "memory_writes": [
            {"salience": 1, "text": "Event 1"},
            {"salience": 1, "text": "Event 2"},
            {"salience": 1, "text": "Event 3"}  # Too many
        ]
    }
    
    with pytest.raises(ValidationError):
        NpcDialogueResponse(**data)


def test_style_tags_max_items():
    """Test that at most 3 style tags are allowed."""
    data = {
        "utterance": "Hello",
        "emotion": "neutral",
        "behavior_directive": "none",
        "style_tags": ["formal", "casual", "whisper", "shout"]  # Too many
    }
    
    with pytest.raises(ValidationError):
        NpcDialogueResponse(**data)


def test_persona_validation():
    """Test persona model validation."""
    persona = Persona(
        name="Elenor",
        role="Elven mage",
        values=["wisdom", "order", "loyalty"],
        quirks=["measured", "formal"],
        backstory=["mentored apothecary", "distrusts smugglers"]
    )
    
    assert persona.name == "Elenor"
    assert len(persona.values) == 3
    assert len(persona.backstory) == 2


def test_game_context_validation():
    """Test game context model validation."""
    context = GameContext(
        scene="Silverwoods_clearing",
        time_of_day="dusk",
        weather="light_rain",
        last_player_action="returned_lost_ring",
        player_reputation=12,
        npc_health=100,
        npc_alertness=0.3
    )
    
    assert context.scene == "Silverwoods_clearing"
    assert context.player_reputation == 12
    assert 0 <= context.npc_alertness <= 1.0


def test_chat_turn_request():
    """Test full chat turn request validation."""
    data = {
        "npc_id": "elenor",
        "player_id": "p1",
        "player_text": "Can you teach me a spell?",
        "persona": {
            "name": "Elenor",
            "role": "Elven mage",
            "values": ["order", "wisdom", "loyalty"],
            "quirks": ["measured", "formal"],
            "backstory": ["mentored apothecary", "distrusts smugglers"]
        },
        "context": {
            "scene": "Silverwoods_clearing",
            "time_of_day": "dusk",
            "weather": "light_rain",
            "last_player_action": "returned_lost_ring",
            "player_reputation": 12,
            "npc_health": 100,
            "npc_alertness": 0.3
        }
    }
    
    request = ChatTurnRequest(**data)
    assert request.npc_id == "elenor"
    assert request.persona.name == "Elenor"
    assert request.context.player_reputation == 12


def test_schema_dict_structure():
    """Test that the JSON Schema dict is properly structured."""
    assert NPC_DIALOGUE_SCHEMA["type"] == "object"
    assert "utterance" in NPC_DIALOGUE_SCHEMA["required"]
    assert "emotion" in NPC_DIALOGUE_SCHEMA["required"]
    assert "behavior_directive" in NPC_DIALOGUE_SCHEMA["required"]
    
    # Check property constraints
    assert NPC_DIALOGUE_SCHEMA["properties"]["utterance"]["maxLength"] == 320
    assert NPC_DIALOGUE_SCHEMA["properties"]["memory_writes"]["maxItems"] == 2
    assert NPC_DIALOGUE_SCHEMA["additionalProperties"] is False


def test_json_serialization():
    """Test that models can be serialized to JSON."""
    response = NpcDialogueResponse(
        utterance="Greetings!",
        emotion=Emotion.HAPPY,
        behavior_directive=BehaviorDirective.APPROACH
    )
    
    json_str = response.model_dump_json()
    data = json.loads(json_str)
    
    assert data["utterance"] == "Greetings!"
    assert data["emotion"] == "happy"
    assert data["behavior_directive"] == "approach"


def test_sample_gemini_output():
    """Test that a realistic Gemini output validates correctly."""
    # Simulated Gemini output (what we expect from the model)
    gemini_output = """
    {
        "utterance": "Ah, you wish to learn the arcane arts? Your recent act of kindness has not gone unnoticed. I may be willing to teach you, if you prove yourself worthy.",
        "emotion": "neutral",
        "style_tags": ["formal", "mystical"],
        "behavior_directive": "none",
        "memory_writes": [
            {
                "salience": 1,
                "text": "Player expressed interest in magic training",
                "keys": ["magic", "training"],
                "private": true
            }
        ],
        "voice_hint": {
            "voice_preset": "feminine_calm",
            "ssml_style": "calm"
        }
    }
    """
    
    data = json.loads(gemini_output)
    response = NpcDialogueResponse(**data)
    
    assert "kindness" in response.utterance
    assert response.emotion == Emotion.NEUTRAL
    assert StyleTag.FORMAL in response.style_tags
    assert len(response.memory_writes) == 1
    assert response.memory_writes[0].salience == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

