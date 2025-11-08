/*
 * WebSocket Client for RPGAI
 * Handles streaming NPC dialogue from the Python backend.
 * 
 * Dependencies: NativeWebSocket (install via Package Manager or GitHub)
 * https://github.com/endel/NativeWebSocket
 */

using UnityEngine;
using System;
using System.Threading.Tasks;
using NativeWebSocket;

namespace RPGAI.Net
{
    /// <summary>
    /// WebSocket message types from server
    /// </summary>
    [Serializable]
    public class WSMessage
    {
        public string type;    // "token" or "final" or "error"
        public string text;    // For type="token"
        public string json;    // For type="final"
        public string message; // For type="error"
    }

    public class LLMWebSocketClient
    {
        private WebSocket ws;
        
        /// <summary>
        /// Fired for each token streamed from the server.
        /// Use this for typewriter effect in dialogue UI.
        /// </summary>
        public event Action<string> OnToken;
        
        /// <summary>
        /// Fired when the complete JSON response is received.
        /// Parse this as NpcResponse to get emotion, behavior, etc.
        /// </summary>
        public event Action<string> OnFinalJson;
        
        /// <summary>
        /// Fired on connection errors.
        /// </summary>
        public event Action<string> OnError;

        /// <summary>
        /// Connect to the WebSocket server.
        /// </summary>
        /// <param name="url">WebSocket URL (e.g., ws://localhost:8000/v1/chat.stream)</param>
        public async Task Connect(string url)
        {
            ws = new WebSocket(url);

            ws.OnOpen += () =>
            {
                Debug.Log($"[WebSocket] Connected to {url}");
            };

            ws.OnMessage += (bytes) =>
            {
                var msgJson = System.Text.Encoding.UTF8.GetString(bytes);
                
                try
                {
                    var msg = JsonUtility.FromJson<WSMessage>(msgJson);
                    
                    if (msg.type == "token")
                    {
                        OnToken?.Invoke(msg.text);
                    }
                    else if (msg.type == "final")
                    {
                        OnFinalJson?.Invoke(msg.json);
                    }
                    else if (msg.type == "error")
                    {
                        Debug.LogError($"[WebSocket] Server error: {msg.message}");
                        OnError?.Invoke(msg.message);
                    }
                }
                catch (Exception e)
                {
                    Debug.LogError($"[WebSocket] Failed to parse message: {e.Message}\n{msgJson}");
                    OnError?.Invoke(e.Message);
                }
            };

            ws.OnError += (e) =>
            {
                Debug.LogError($"[WebSocket] Error: {e}");
                OnError?.Invoke(e);
            };

            ws.OnClose += (e) =>
            {
                Debug.Log($"[WebSocket] Closed with code {e}");
            };

            await ws.Connect();
        }

        /// <summary>
        /// Send a single JSON payload (the chat turn).
        /// After this, listen to OnToken and OnFinalJson events.
        /// </summary>
        /// <param name="jsonPayload">JSON string of ChatTurnRequest</param>
        public async Task SendOnce(string jsonPayload)
        {
            if (ws == null || ws.State != WebSocketState.Open)
            {
                Debug.LogError("[WebSocket] Cannot send: not connected");
                return;
            }

            await ws.SendText(jsonPayload);
            Debug.Log("[WebSocket] Sent chat turn");
        }

        /// <summary>
        /// Close the WebSocket connection.
        /// </summary>
        public async Task Close()
        {
            if (ws != null)
            {
                await ws.Close();
                ws = null;
            }
        }

        /// <summary>
        /// Call this in your MonoBehaviour's Update() to process messages.
        /// WebSocket messages are queued and dispatched on Update.
        /// </summary>
        public void DispatchMessages()
        {
#if !UNITY_WEBGL || UNITY_EDITOR
            ws?.DispatchMessageQueue();
#endif
        }
    }
}

