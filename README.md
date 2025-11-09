# RPGAI - Intelligent NPC Dialogue System

> **LLM-powered NPC dialogue with memory and TTS for Unity games**

A production-ready FastAPI backend that brings NPCs to life using:
- 🧠 **Gemini** for contextual, personality-driven dialogue with structured JSON output
- 💾 **SQLite** for lightweight NPC memory (salience × recency retrieval)
- 🎙️ **Google Cloud TTS** for emotional voice synthesis with SSML
- 🔌 **WebSocket streaming** for real-time typewriter effects

---

## 📦 Project Structure

```
rpgai/
├── server/                      # Python FastAPI Backend
│   ├── main.py                  # FastAPI app: WebSocket chat, memory, TTS
│   ├── llm_client.py            # Gemini client with structured output
│   ├── schemas.py               # Pydantic models + JSON Schema
│   ├── memory.py                # SQLite DAO (salience/recency retrieval)
│   ├── tts.py                   # Google Cloud TTS (SSML)
│   ├── settings.py              # Configuration management
│   └── requirements.txt         # Python dependencies
├── tests/                       # Unit tests
│   ├── test_memory.py
│   └── test_schema.py
├── unity/Assets/Scripts/        # Unity C# Templates
│   ├── Net/
│   │   ├── HttpClient.cs        # UnityWebRequest JSON helpers
│   │   └── LLMWebSocketClient.cs # WebSocket streaming client
│   ├── Dialogue/
│   │   ├── DialogueController.cs # Main dialogue orchestrator
│   │   └── NpcResponse.cs       # Response data models
│   ├── State/
│   │   └── GameContextProvider.cs # Game state context
│   └── Audio/
│       └── TTSPlayer.cs         # TTS audio playback
├── media/                       # Generated audio files (gitignored)
├── .env                         # API keys (create from .env.example)
└── README.md                    # This file
```

---

## 🚀 Quick Start

### Prerequisites

- **Python 3.9+**
- **Gemini API Key** ([Get one here](https://ai.google.dev/))
- **Google Cloud Account** with Text-to-Speech and Speech-to-Text APIs enabled
- **Unity 2021.3+** (for client-side integration)

### 1. Backend Setup

```bash
# Clone or navigate to the project
cd rpgai

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r server/requirements.txt

# Configure environment variables
cp .env.example .env
# Edit .env and add:
#   GEMINI_API_KEY=your_key_here
#   GOOGLE_APPLICATION_CREDENTIALS=/path/to/gcp-credentials.json
```

### 2. Run the Server

```bash
# Development mode (auto-reload)
uvicorn server.main:app --reload --port 8000

# Production mode
uvicorn server.main:app --host 0.0.0.0 --port 8000 --workers 4
```

Server will be available at:
- **API Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/healthz
- **WebSocket**: ws://localhost:8000/v1/chat.stream

### 3. Run Tests

```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_memory.py -v

# With coverage
pytest tests/ --cov=server --cov-report=html
```

---

## 🔧 Configuration

### Environment Variables (.env)

```bash
# Gemini API
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-2.0-flash-exp

# Google Cloud TTS
GOOGLE_APPLICATION_CREDENTIALS=/path/to/gcp-credentials.json

# Server
HOST=0.0.0.0
PORT=8000
LOG_LEVEL=INFO

# Database
DB_PATH=npc_memory.db

# Media Storage
MEDIA_DIR=./media
MEDIA_BASE_URL=http://localhost:8000/media

# Model Parameters
TEMPERATURE=0.7
TOP_P=0.9
MAX_OUTPUT_TOKENS=220
```

### Google Cloud Audio APIs Setup

1. Create a GCP project and enable:
   - **Text-to-Speech API** (for NPC voice output)
   - **Speech-to-Text API** (for player voice input)
2. Create a service account with appropriate permissions
3. Download the JSON service account key
4. Set `GOOGLE_APPLICATION_CREDENTIALS` to the path of your JSON key

```bash
# Enable APIs (using gcloud CLI)
gcloud services enable texttospeech.googleapis.com
gcloud services enable speech.googleapis.com
```

---

## 📡 API Reference

### WebSocket: Streaming Chat

**Endpoint**: `ws://localhost:8000/v1/chat.stream`

**Flow**:
1. Client connects
2. Client sends ONE JSON message (ChatTurnRequest)
3. Server streams tokens: `{"type":"token", "text":"..."}`
4. Server sends final: `{"type":"final", "json":"{...NpcDialogueResponse}"}`

**Request Payload**:
```json
{
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
```

**Response Stream**:
```json
{"type": "token", "text": "Ah, "}
{"type": "token", "text": "you wish to "}
{"type": "token", "text": "learn magic? "}
{"type": "final", "json": "{\"utterance\":\"Ah, you wish to learn magic? Very well.\",\"emotion\":\"neutral\",\"behavior_directive\":\"none\",\"memory_writes\":[{\"salience\":1,\"text\":\"Player asked about magic training\"}]}"}
```

---

### HTTP: Memory Management

#### Write Memory
```bash
POST /v1/memory/write
Content-Type: application/json

{
  "npc_id": "elenor",
  "player_id": "p1",
  "text": "Player returned lost ring",
  "salience": 2,
  "keys": ["ring", "kindness"],
  "private": true
}

# Response
{"ok": true, "id": 1}
```

#### Get Top Memories
```bash
GET /v1/memory/top?npc_id=elenor&player_id=p1&k=3

# Response
{
  "memories": [
    {
      "id": 1,
      "npc_id": "elenor",
      "player_id": "p1",
      "text": "Player returned lost ring",
      "salience": 2,
      "private": true,
      "keys": "[\"ring\", \"kindness\"]",
      "ts": 1699564800
    }
  ]
}
```

---

### HTTP: Text-to-Speech

```bash
POST /v1/voice/tts
Content-Type: application/json

{
  "ssml": "<speak><prosody rate='95%' pitch='+1st'>Greetings, traveler.</prosody></speak>",
  "voice_name": "en-US-Neural2-C"
}

# Response
{
  "audio_url": "http://localhost:8000/media/abc123.mp3"
}
```

**Available Voice Presets**:
- `en-US-Neural2-C` - Feminine, calm (default)
- `en-US-Neural2-F` - Feminine, young
- `en-US-Neural2-D` - Masculine, deep
- `en-US-Neural2-A` - Masculine, casual
- `en-GB-Neural2-B` - Elderly, wise

---

### HTTP: Speech-to-Text

```bash
POST /v1/voice/stt
Content-Type: multipart/form-data

# Form fields:
# - audio: Audio file (WAV, MP3, FLAC, OGG, WEBM)
# - language_code: Language code (default: en-US)

# Response
{
  "text": "Hello, I would like to buy some potions",
  "confidence": 0.95
}
```

**Usage Example (curl)**:
```bash
# Record audio (on macOS/Linux)
ffmpeg -f avfoundation -i ":0" -t 5 recording.wav

# Or on Windows
# ffmpeg -f dshow -i audio="Microphone" -t 5 recording.wav

# Send to STT endpoint
curl -X POST http://localhost:8000/v1/voice/stt \
  -F "audio=@recording.wav" \
  -F "language_code=en-US"
```

**Workflow with Voice Input**:
1. Player records audio in Unity using `Microphone.Start()`
2. Unity converts audio to WAV/MP3 and sends to `/v1/voice/stt`
3. Server transcribes audio to text using GCP Speech-to-Text
4. Unity receives transcribed text and uses it as `player_text` in dialogue request

See Unity README for complete voice input implementation example.

---

## 🎮 Unity Integration

### 1. Install Dependencies

Install **NativeWebSocket** via Unity Package Manager:
```
https://github.com/endel/NativeWebSocket.git#upm
```

### 2. Setup Scene

1. Create an empty GameObject called `DialogueSystem`
2. Attach `DialogueController` component
3. Attach `GameContextProvider` component
4. Create another GameObject called `TTSPlayer` and attach the `TTSPlayer` component
5. Wire references in the Inspector

### 3. Example Usage

```csharp
using RPGAI.Dialogue;
using RPGAI.Audio;

public class PlayerInteraction : MonoBehaviour
{
    [SerializeField] private DialogueController dialogue;
    [SerializeField] private TTSPlayer ttsPlayer;
    
    private NpcPersona elenorPersona = new NpcPersona
    {
        name = "Elenor",
        role = "Elven mage",
        values = new[] { "order", "wisdom", "loyalty" },
        quirks = new[] { "measured", "formal" },
        backstory = new[] { "mentored apothecary", "distrusts smugglers" }
    };
    
    async void Start()
    {
        // Subscribe to events
        dialogue.OnTokenReceived += ShowToken;
        dialogue.OnResponseComplete += HandleResponse;
        
        // Send a message
        await dialogue.SendPlayerMessage(
            "elenor",
            "Can you teach me a spell?",
            elenorPersona
        );
    }
    
    private void ShowToken(string token)
    {
        // Update UI with typewriter effect
        Debug.Log($"Token: {token}");
    }
    
    private async void HandleResponse(NpcResponse response)
    {
        Debug.Log($"Utterance: {response.utterance}");
        Debug.Log($"Emotion: {response.emotion}");
        Debug.Log($"Behavior: {response.behavior_directive}");
        
        // Apply emotion to animator
        // animator.SetTrigger(response.emotion.ToString());
        
        // Execute behavior
        // behaviorTree.Execute(response.behavior_directive);
        
        // Play TTS
        await ttsPlayer.PlayTTS(response.utterance);
    }
}
```

---

## 🧪 Testing the System

### Test WebSocket with Python

```python
import asyncio
import websockets
import json

async def test_chat():
    uri = "ws://localhost:8000/v1/chat.stream"
    async with websockets.connect(uri) as websocket:
        payload = {
            "npc_id": "elenor",
            "player_id": "p1",
            "player_text": "Hello!",
            "persona": {
                "name": "Elenor",
                "role": "Elven mage",
                "values": ["wisdom"],
                "quirks": ["formal"],
                "backstory": ["lives in forest"]
            },
            "context": {
                "scene": "forest",
                "time_of_day": "noon",
                "weather": "clear",
                "player_reputation": 0,
                "npc_health": 100,
                "npc_alertness": 0.0
            }
        }
        
        await websocket.send(json.dumps(payload))
        
        async for message in websocket:
            data = json.loads(message)
            if data["type"] == "token":
                print(data["text"], end="", flush=True)
            elif data["type"] == "final":
                print(f"\n\nFinal JSON: {data['json']}")
                break

asyncio.run(test_chat())
```

### Test TTS with curl

```bash
curl -X POST http://localhost:8000/v1/voice/tts \
  -H "Content-Type: application/json" \
  -d '{
    "ssml": "<speak>Greetings, traveler.</speak>",
    "voice_name": "en-US-Neural2-C"
  }'

# Response: {"audio_url":"http://localhost:8000/media/abc123.mp3"}
# Visit the URL in your browser to play the audio
```

---

## 📊 JSON Schema (Structured Output)

The LLM is configured to ALWAYS return JSON matching this schema:

```json
{
  "utterance": "string (max 320 chars)",
  "emotion": "neutral|happy|angry|fear|sad|surprised|disgust",
  "style_tags": ["formal", "whisper", ...],  // optional, max 3
  "behavior_directive": "none|approach|step_back|flee|attack|call_guard|give_item|start_quest|open_shop|heal_player",
  "memory_writes": [  // optional, max 2
    {
      "salience": 0-3,
      "text": "string (max 160 chars)",
      "keys": ["keyword1", ...],  // optional, max 4
      "private": true
    }
  ],
  "public_events": [  // optional, max 1
    {
      "event_type": "string",
      "payload": {}
    }
  ],
  "voice_hint": {  // optional
    "voice_preset": "string",
    "ssml_style": "default|narration|whispered|shouted|urgent|calm"
  }
}
```

---

## 🎯 How It Works

### Dialogue Flow

1. **Unity sends context** → WebSocket with persona + game state + player text
2. **Backend retrieves memories** → Top 3 by salience × recency
3. **Gemini generates response** → Structured JSON with emotion, behavior, utterance
4. **Backend streams tokens** → Unity shows typewriter effect
5. **Backend sends final JSON** → Unity parses and applies
6. **Unity triggers actions** → Animation, behavior tree, TTS playback
7. **Memories auto-saved** → Backend writes memory_writes to SQLite

### Memory System

- **Salience** (0-3): Importance level (3 = critical, 0 = trivial)
- **Recency**: Unix timestamp
- **Retrieval**: `ORDER BY salience DESC, ts DESC LIMIT k`
- **Isolation**: Memories are per (npc_id, player_id) pair

### Example Memory Evolution

```
Turn 1: Player steals item
  → Memory: "Player stole potion" (salience=3)
  → NPC: "How dare you! Guards!" (emotion=angry, behavior=call_guard)

Turn 2: Player returns later
  → Retrieves: "Player stole potion" (salience=3)
  → NPC: "You! Get out of my shop!" (emotion=angry, behavior=step_back)

Turn 3: Player gives gift
  → Retrieves: "Player stole potion" (salience=3)
  → Memory: "Player gave gift as apology" (salience=2)
  → NPC: "Perhaps... I misjudged you." (emotion=neutral, behavior=none)
```

---

## 🛠️ Production Deployment

### Using Docker

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY server/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY server/ ./server/

EXPOSE 8000

CMD ["uvicorn", "server.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

```bash
# Build and run
docker build -t rpgai .
docker run -p 8000:8000 --env-file .env rpgai
```

### Using Systemd

```ini
# /etc/systemd/system/rpgai.service
[Unit]
Description=RPGAI NPC Dialogue Service
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/rpgai
Environment="PATH=/opt/rpgai/venv/bin"
ExecStart=/opt/rpgai/venv/bin/uvicorn server.main:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

### Environment Security

- ❌ Never commit `.env` to git
- ✅ Use secret managers (AWS Secrets Manager, GCP Secret Manager)
- ✅ Restrict CORS origins in production
- ✅ Enable HTTPS (use Nginx/Caddy as reverse proxy)
- ✅ Rate limit WebSocket connections

---

## 🐛 Troubleshooting

### "GEMINI_API_KEY not set"
→ Create `.env` file with `GEMINI_API_KEY=your_key`

### "TTS synthesis failed"
→ Check `GOOGLE_APPLICATION_CREDENTIALS` path is correct  
→ Verify GCP Text-to-Speech API is enabled  
→ Check service account has TTS permissions

### WebSocket disconnects immediately
→ Check firewall allows WebSocket connections  
→ Verify Unity's WebSocket URL matches server address  
→ Check server logs: `tail -f logs/rpgai.log`

### Invalid JSON from Gemini
→ Check `NPC_DIALOGUE_SCHEMA` matches `NpcDialogueResponse`  
→ Increase `max_output_tokens` if responses are truncated  
→ Review system instruction for clarity

### Slow response times
→ Use `gemini-1.5-flash` instead of `gemini-2.0-flash-exp`  
→ Reduce `MAX_OUTPUT_TOKENS` (default 220)  
→ Cache system instruction (future enhancement)

---

## 📚 References

- [Gemini API Docs](https://ai.google.dev/docs)
- [Gemini Structured Output](https://ai.google.dev/docs/structured_output)
- [Google Cloud TTS](https://cloud.google.com/text-to-speech/docs)
- [FastAPI WebSockets](https://fastapi.tiangolo.com/advanced/websockets/)
- [NativeWebSocket for Unity](https://github.com/endel/NativeWebSocket)

---

## 📝 License

MIT License - see LICENSE file for details.

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

---

## 🎮 Built for RPGAI Hackathon

This project implements the **RPGAI challenge** requirements:
- ✅ Dynamic AI dialogues with personality-driven responses
- ✅ Integrated game prototype (Unity templates provided)
- ✅ In-game context integration (weather, reputation, actions)
- ✅ Character memory system with salience ranking
- ✅ Emotional & behavioral reactions
- ✅ Voice integration (Google Cloud TTS)

**What makes this special:**
- **Production-ready** architecture (not just a proof-of-concept)
- **Structured output** ensures Unity never receives malformed JSON
- **Memory system** creates persistent relationships between player and NPCs
- **Streaming responses** for smooth UX (typewriter effect)
- **Comprehensive documentation** for easy integration

---

Made with ❤️ for immersive RPG experiences.

**Questions?** Open an issue or check `/docs` for interactive API documentation.

