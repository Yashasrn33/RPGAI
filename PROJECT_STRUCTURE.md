# RPGAI Project Structure

## Complete File Tree

```
rpgai/
│
├── 📄 README.md                      # Comprehensive documentation
├── 📄 QUICKSTART.md                  # 5-minute setup guide
├── 📄 PROJECT_STRUCTURE.md           # This file
├── 🔧 setup.sh                       # Automated setup script
├── 🔒 .env.example                   # Environment template
├── 🔒 .env                           # Your API keys (gitignored)
├── 🚫 .gitignore                     # Git ignore rules
│
├── 📁 server/                        # Python FastAPI Backend
│   ├── __init__.py                   # Package init
│   ├── main.py                       # 🔥 FastAPI app entry point
│   ├── llm_client.py                 # 🧠 Gemini client with structured output
│   ├── schemas.py                    # 📋 Pydantic models + JSON Schema
│   ├── memory.py                     # 💾 SQLite DAO for NPC memory
│   ├── tts.py                        # 🎙️ Google Cloud TTS wrapper
│   ├── settings.py                   # ⚙️ Configuration management
│   └── requirements.txt              # 📦 Python dependencies
│
├── 📁 tests/                         # Unit Tests
│   ├── __init__.py
│   ├── test_memory.py                # Memory system tests
│   └── test_schema.py                # Schema validation tests
│
├── 📁 unity/                         # Unity C# Integration
│   ├── README.md                     # Unity-specific guide
│   └── Assets/Scripts/
│       │
│       ├── Net/                      # Networking layer
│       │   ├── HttpClient.cs         # UnityWebRequest helpers
│       │   └── LLMWebSocketClient.cs # WebSocket streaming
│       │
│       ├── Dialogue/                 # Dialogue system
│       │   ├── DialogueController.cs # Main orchestrator
│       │   └── NpcResponse.cs        # Response data models
│       │
│       ├── State/                    # Game state
│       │   └── GameContextProvider.cs # Context builder
│       │
│       └── Audio/                    # TTS playback
│           └── TTSPlayer.cs          # Audio synthesis & playback
│
├── 📁 media/                         # Generated audio files
│   └── *.mp3                         # (gitignored, created at runtime)
│
└── 📁 venv/                          # Python virtual environment
    └── ...                           # (gitignored)
```

## Component Responsibilities

### Backend (Python/FastAPI)

| File | Purpose | Key Features |
|------|---------|--------------|
| **main.py** | API entry point | WebSocket streaming, HTTP endpoints, CORS |
| **llm_client.py** | Gemini integration | Structured output, JSON validation, streaming |
| **schemas.py** | Data contracts | Pydantic models, JSON Schema, enums |
| **memory.py** | NPC memory DB | SQLite DAO, salience×recency retrieval |
| **tts.py** | Voice synthesis | SSML generation, Google Cloud TTS |
| **settings.py** | Configuration | .env loading, validation |

### Frontend (Unity/C#)

| File | Purpose | Key Features |
|------|---------|--------------|
| **DialogueController.cs** | Main orchestrator | WebSocket management, event handling |
| **LLMWebSocketClient.cs** | WS client | Token streaming, message parsing |
| **HttpClient.cs** | HTTP utilities | JSON POST/GET helpers |
| **NpcResponse.cs** | Data models | Response parsing, enums |
| **GameContextProvider.cs** | Context builder | Scene state, reputation tracking |
| **TTSPlayer.cs** | Audio playback | TTS download & playback |

## Data Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                         Unity (C#)                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Player Input → DialogueController                             │
│                       ↓                                         │
│             GameContextProvider (builds context)               │
│                       ↓                                         │
│             LLMWebSocketClient.SendOnce(payload)              │
│                       ↓                                         │
└───────────────────────┼─────────────────────────────────────────┘
                        │
                        │ WebSocket: ws://host/v1/chat.stream
                        ↓
┌─────────────────────────────────────────────────────────────────┐
│                    FastAPI Backend (Python)                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. main.py: Accept WebSocket connection                       │
│                       ↓                                         │
│  2. memory.py: Retrieve top-3 memories (salience×recency)      │
│                       ↓                                         │
│  3. llm_client.py: Build prompt with persona + context + mem   │
│                       ↓                                         │
│  4. Gemini API: Generate structured JSON response              │
│                       ↓                                         │
│  5. Stream tokens back: {"type":"token", "text":"..."}         │
│                       ↓                                         │
│  6. Send final JSON: {"type":"final", "json":"{...}"}          │
│                       ↓                                         │
│  7. Auto-write memory_writes to SQLite                         │
│                                                                 │
└───────────────────────┼─────────────────────────────────────────┘
                        │
                        │ Stream back to Unity
                        ↓
┌─────────────────────────────────────────────────────────────────┐
│                         Unity (C#)                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  OnToken events → Update UI (typewriter effect)                │
│                       ↓                                         │
│  OnFinalJson → Parse NpcResponse                               │
│                       ↓                                         │
│  Apply emotion → Animator.SetTrigger(emotion)                  │
│  Apply behavior → Execute(behavior_directive)                  │
│                       ↓                                         │
│  TTSPlayer.PlayTTS(utterance) → Download & play audio          │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## API Endpoints

### WebSocket

```
ws://localhost:8000/v1/chat.stream
├─ Accepts: ChatTurnRequest
├─ Streams: {"type":"token",...} (multiple)
└─ Returns: {"type":"final","json":"..."} (once)
```

### HTTP

```
http://localhost:8000/
├─ GET  /healthz              # Server health check
├─ GET  /                     # API info
│
├─ POST /v1/memory/write      # Write memory entry
├─ GET  /v1/memory/top        # Get top-k memories
├─ GET  /v1/memory/all/{npc}  # Get all NPC memories
│
├─ POST /v1/voice/tts         # Synthesize speech
│
└─ GET  /docs                 # Interactive API docs
```

## Database Schema

```sql
-- SQLite: npc_memory.db

CREATE TABLE npc_memory (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    npc_id TEXT NOT NULL,
    player_id TEXT NOT NULL,
    text TEXT NOT NULL,
    salience INTEGER NOT NULL CHECK(salience >= 0 AND salience <= 3),
    private INTEGER NOT NULL DEFAULT 1,
    keys TEXT,        -- JSON array
    ts INTEGER NOT NULL
);

CREATE INDEX idx_mem_query 
ON npc_memory(npc_id, player_id, salience DESC, ts DESC);
```

## Configuration

### Backend (.env)

```bash
GEMINI_API_KEY=...            # Required
GEMINI_MODEL=...              # Optional (default: gemini-2.0-flash-exp)
GOOGLE_APPLICATION_CREDENTIALS=...  # Optional (for TTS)
HOST=0.0.0.0                  # Server host
PORT=8000                     # Server port
LOG_LEVEL=INFO                # DEBUG|INFO|WARNING|ERROR
DB_PATH=npc_memory.db         # SQLite file path
MEDIA_DIR=./media             # Audio output directory
TEMPERATURE=0.7               # LLM creativity
TOP_P=0.9                     # Nucleus sampling
MAX_OUTPUT_TOKENS=220         # Response length limit
```

### Unity Inspector

```
DialogueController:
  ├─ Server URL: ws://localhost:8000/v1/chat.stream
  └─ Context Provider: (reference)

GameContextProvider:
  ├─ Scene Name: "forest"
  ├─ Time of Day: "noon"
  ├─ Weather: "clear"
  ├─ Player Reputation: 0
  ├─ NPC Health: 100
  └─ NPC Alertness: 0.0

TTSPlayer:
  ├─ TTS Endpoint: http://localhost:8000/v1/voice/tts
  └─ Audio Source: (auto-attached)
```

## Dependencies

### Python (requirements.txt)

```
fastapi==0.109.0              # Web framework
uvicorn[standard]==0.27.0     # ASGI server
google-genai==1.0.0           # Gemini SDK
google-cloud-texttospeech==2.16.0  # TTS SDK
pydantic==2.5.3               # Data validation
python-dotenv==1.0.0          # Config management
aiosqlite==0.19.0             # Async SQLite
pytest==7.4.4                 # Testing
```

### Unity (Package Manager)

```
NativeWebSocket               # WebSocket client
  → https://github.com/endel/NativeWebSocket.git#upm
```

## Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| **Structured JSON Output** | Ensures Unity never receives malformed data |
| **WebSocket Streaming** | Low latency, typewriter effect, real-time feel |
| **SQLite Memory** | Lightweight, no external DB needed, file-based |
| **Salience×Recency** | Recent important events surface first |
| **SSML for TTS** | Fine control over prosody, emotion-aware speech |
| **Per-NPC Memory** | NPCs remember player differently |
| **Async/Await** | Non-blocking I/O, responsive gameplay |
| **Pydantic Validation** | Type safety, auto-docs, error handling |

## Testing Strategy

```
Unit Tests:
├─ test_memory.py
│   ├─ Write/read operations
│   ├─ Salience ordering
│   ├─ Recency ordering
│   ├─ NPC/player isolation
│   └─ Edge cases
│
└─ test_schema.py
    ├─ Pydantic validation
    ├─ Enum constraints
    ├─ Field limits
    └─ Sample Gemini outputs

Integration Tests:
└─ (Coming soon: WebSocket E2E, TTS synthesis)
```

## Production Checklist

- [ ] Environment secrets (not in .env)
- [ ] CORS origin restrictions
- [ ] HTTPS/WSS (not HTTP/WS)
- [ ] Rate limiting
- [ ] Request logging
- [ ] Error monitoring (Sentry)
- [ ] Health checks
- [ ] Database backups
- [ ] Load balancing
- [ ] WebSocket connection limits

---

**For detailed usage, see [`README.md`](./README.md)**  
**For quick setup, see [`QUICKSTART.md`](./QUICKSTART.md)**

