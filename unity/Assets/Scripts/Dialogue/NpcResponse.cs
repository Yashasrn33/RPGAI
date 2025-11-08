/*
 * NPC Response Data Model
 * C# mirror of the Python NpcDialogueResponse schema.
 */

using UnityEngine;
using System;
using System.Collections.Generic;

namespace RPGAI.Dialogue
{
    /// <summary>
    /// Emotions an NPC can express.
    /// </summary>
    public enum Emotion
    {
        neutral,
        happy,
        angry,
        fear,
        sad,
        surprised,
        disgust
    }

    /// <summary>
    /// Actions the NPC should perform.
    /// </summary>
    public enum BehaviorDirective
    {
        none,
        approach,
        step_back,
        flee,
        attack,
        call_guard,
        give_item,
        start_quest,
        open_shop,
        heal_player
    }

    /// <summary>
    /// Memory entry to be written.
    /// </summary>
    [Serializable]
    public class MemoryWrite
    {
        public int salience;         // 0-3
        public string text;          // Max 160 chars
        public string[] keys;        // Optional search keywords
        public bool @private = true; // Private to this NPC
    }

    /// <summary>
    /// Public event visible to other NPCs.
    /// </summary>
    [Serializable]
    public class PublicEvent
    {
        public string event_type;
        public Dictionary<string, object> payload;
    }

    /// <summary>
    /// Voice synthesis hints.
    /// </summary>
    [Serializable]
    public class VoiceHint
    {
        public string voice_preset;  // e.g., "feminine_calm"
        public string ssml_style;    // e.g., "calm", "urgent"
    }

    /// <summary>
    /// Complete NPC dialogue response from the LLM.
    /// Deserialize the "json" field from the WebSocket "final" message into this.
    /// </summary>
    [Serializable]
    public class NpcResponse
    {
        public string utterance;                    // What the NPC says
        public Emotion emotion;                     // Current emotion
        public string[] style_tags;                 // Speech style (max 3)
        public BehaviorDirective behavior_directive; // Action to perform
        public MemoryWrite[] memory_writes;         // Memories to save
        public PublicEvent[] public_events;         // World events
        public VoiceHint voice_hint;                // TTS config

        /// <summary>
        /// Parse from JSON string.
        /// </summary>
        public static NpcResponse FromJson(string json)
        {
            try
            {
                return JsonUtility.FromJson<NpcResponse>(json);
            }
            catch (Exception e)
            {
                Debug.LogError($"Failed to parse NpcResponse: {e.Message}\n{json}");
                return null;
            }
        }
    }
}

