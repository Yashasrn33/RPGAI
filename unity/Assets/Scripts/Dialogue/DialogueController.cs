/*
 * Dialogue Controller
 * Orchestrates NPC conversations: sends player input, receives streaming responses,
 * triggers animations and behaviors.
 */

using UnityEngine;
using System.Threading.Tasks;
using RPGAI.Net;
using RPGAI.State;

namespace RPGAI.Dialogue
{
    public class DialogueController : MonoBehaviour
    {
        [Header("Backend Configuration")]
        [SerializeField] private string serverUrl = "ws://localhost:8000/v1/chat.stream";

        [Header("References")]
        [SerializeField] private GameContextProvider contextProvider;

        private LLMWebSocketClient wsClient;
        private string currentNpcId;
        private string playerId = "p1"; // TODO: Get from player system

        // Events for UI and gameplay systems
        public event System.Action<string> OnTokenReceived;  // Typewriter effect
        public event System.Action<NpcResponse> OnResponseComplete;

        private void Awake()
        {
            wsClient = new LLMWebSocketClient();
            wsClient.OnToken += HandleToken;
            wsClient.OnFinalJson += HandleFinalJson;
            wsClient.OnError += HandleError;
        }

        private void Update()
        {
            // Required for WebSocket message dispatching
            wsClient?.DispatchMessages();
        }

        /// <summary>
        /// Start a conversation with an NPC.
        /// </summary>
        /// <param name="npcId">NPC identifier (e.g., "elenor")</param>
        /// <param name="playerText">What the player said</param>
        /// <param name="persona">NPC personality definition</param>
        public async Task SendPlayerMessage(string npcId, string playerText, NpcPersona persona)
        {
            currentNpcId = npcId;

            // Connect if not already
            if (wsClient == null || !IsConnected())
            {
                await wsClient.Connect(serverUrl);
            }

            // Build the chat turn payload
            var context = contextProvider.GetCurrentContext();
            var payload = new ChatTurnPayload
            {
                npc_id = npcId,
                player_id = playerId,
                player_text = playerText,
                persona = persona,
                context = context
            };

            string json = JsonUtility.ToJson(payload);
            Debug.Log($"[Dialogue] Sending to {npcId}: {playerText}");

            await wsClient.SendOnce(json);
        }

        private void HandleToken(string token)
        {
            // Forward to UI for typewriter effect
            OnTokenReceived?.Invoke(token);
        }

        private void HandleFinalJson(string json)
        {
            Debug.Log($"[Dialogue] Final response: {json}");

            var response = NpcResponse.FromJson(json);
            if (response == null)
            {
                Debug.LogError("[Dialogue] Failed to parse NPC response");
                return;
            }

            // Fire event for gameplay systems
            OnResponseComplete?.Invoke(response);

            // TODO: Apply emotion to animator
            // TODO: Execute behavior_directive
            // TODO: Write memories to backend
            // TODO: Trigger TTS
        }

        private void HandleError(string error)
        {
            Debug.LogError($"[Dialogue] WebSocket error: {error}");
        }

        private bool IsConnected()
        {
            // Check WebSocket state (implementation depends on NativeWebSocket version)
            return true; // Placeholder
        }

        private void OnDestroy()
        {
            wsClient?.Close();
        }
    }

    // ========================================================================
    // PAYLOAD MODELS (for sending to backend)
    // ========================================================================

    [System.Serializable]
    public class ChatTurnPayload
    {
        public string npc_id;
        public string player_id;
        public string player_text;
        public NpcPersona persona;
        public GameContext context;
    }

    [System.Serializable]
    public class NpcPersona
    {
        public string name;
        public string role;
        public string[] values;
        public string[] quirks;
        public string[] backstory;
    }
}

