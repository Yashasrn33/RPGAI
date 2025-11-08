/*
 * Game Context Provider
 * Gathers current game state (scene, weather, time, reputation, etc.)
 * to send to the LLM for contextual dialogue.
 */

using UnityEngine;

namespace RPGAI.State
{
    [System.Serializable]
    public class GameContext
    {
        public string scene;              // Current location name
        public string time_of_day;        // e.g., "dawn", "dusk", "night"
        public string weather;            // e.g., "clear", "light_rain", "storm"
        public string last_player_action; // Most recent player action
        public int player_reputation;     // -10 to +20 (affects NPC behavior)
        public int npc_health;            // NPC health (0-100)
        public float npc_alertness;       // NPC alertness level (0-1)
    }

    public class GameContextProvider : MonoBehaviour
    {
        [Header("Static Context")]
        [SerializeField] private string sceneName = "Silverwoods_clearing";
        
        [Header("Dynamic State")]
        [SerializeField] private string timeOfDay = "dusk";
        [SerializeField] private string weather = "clear";
        [SerializeField] private int playerReputation = 0;

        [Header("NPC State")]
        [SerializeField] private int npcHealth = 100;
        [SerializeField] private float npcAlertness = 0.0f;

        private string lastPlayerAction = "none";

        /// <summary>
        /// Get the current game context for the LLM.
        /// </summary>
        public GameContext GetCurrentContext()
        {
            return new GameContext
            {
                scene = sceneName,
                time_of_day = timeOfDay,
                weather = weather,
                last_player_action = lastPlayerAction,
                player_reputation = playerReputation,
                npc_health = npcHealth,
                npc_alertness = npcAlertness
            };
        }

        /// <summary>
        /// Update the last player action (call from gameplay systems).
        /// </summary>
        public void SetLastPlayerAction(string action)
        {
            lastPlayerAction = action;
            Debug.Log($"[Context] Last player action: {action}");
        }

        /// <summary>
        /// Modify player reputation (e.g., after good/bad deeds).
        /// </summary>
        public void ModifyReputation(int delta)
        {
            playerReputation = Mathf.Clamp(playerReputation + delta, -10, 20);
            Debug.Log($"[Context] Reputation: {playerReputation}");
        }

        /// <summary>
        /// Set time of day (hook to day/night cycle system).
        /// </summary>
        public void SetTimeOfDay(string time)
        {
            timeOfDay = time;
        }

        /// <summary>
        /// Set weather (hook to weather system).
        /// </summary>
        public void SetWeather(string weatherType)
        {
            weather = weatherType;
        }

        /// <summary>
        /// Update NPC state (health, alertness).
        /// </summary>
        public void UpdateNpcState(int health, float alertness)
        {
            npcHealth = Mathf.Clamp(health, 0, 100);
            npcAlertness = Mathf.Clamp01(alertness);
        }
    }
}

