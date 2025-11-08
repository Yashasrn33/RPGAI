# 🚀 RPGAI Quick Start

Get up and running in 5 minutes!

## Step 1: Setup Backend (2 minutes)

```bash
# Run the setup script
chmod +x setup.sh
./setup.sh

# Or manually:
python3 -m venv venv
source venv/bin/activate
pip install -r server/requirements.txt
```

## Step 2: Configure API Keys (1 minute)

Edit `.env` file:

```bash
# Get Gemini API key from: https://ai.google.dev/
GEMINI_API_KEY=your_actual_key_here

# Get GCP credentials for TTS (optional for testing)
GOOGLE_APPLICATION_CREDENTIALS=/path/to/gcp-key.json
```

## Step 3: Start Server (30 seconds)

```bash
source venv/bin/activate
uvicorn server.main:app --reload --port 8000
```

Server running at: http://localhost:8000

## Step 4: Test It! (1 minute)

### Test Health Check

```bash
curl http://localhost:8000/healthz
```

Expected: `{"ok": true, "service": "rpgai", ...}`

### Test WebSocket Chat

Create `test_chat.py`:

```python
import asyncio
import websockets
import json

async def test():
    uri = "ws://localhost:8000/v1/chat.stream"
    async with websockets.connect(uri) as ws:
        await ws.send(json.dumps({
            "npc_id": "elenor",
            "player_id": "p1",
            "player_text": "Hello!",
            "persona": {
                "name": "Elenor",
                "role": "Mage",
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
        }))
        
        async for msg in ws:
            data = json.loads(msg)
            if data["type"] == "token":
                print(data["text"], end="", flush=True)
            elif data["type"] == "final":
                print(f"\n\n✓ Complete!")
                break

asyncio.run(test())
```

Run: `python test_chat.py`

## Unity Integration

### 1. Install NativeWebSocket

Unity Package Manager → Add from Git URL:
```
https://github.com/endel/NativeWebSocket.git#upm
```

### 2. Copy Unity Scripts

Copy `unity/Assets/Scripts/` to your Unity project

### 3. Create GameObjects

```
DialogueSystem
├─ DialogueController
└─ GameContextProvider

TTSPlayer
├─ AudioSource
└─ TTSPlayer
```

### 4. Usage

```csharp
var persona = new NpcPersona {
    name = "Elenor",
    role = "Mage",
    values = new[] { "wisdom" },
    quirks = new[] { "formal" },
    backstory = new[] { "lives in forest" }
};

await dialogue.SendPlayerMessage("elenor", "Hello!", persona);
```

## Common Commands

```bash
# Start server
uvicorn server.main:app --reload

# Run tests
pytest tests/ -v

# Check health
curl http://localhost:8000/healthz

# View API docs
open http://localhost:8000/docs
```

## Troubleshooting

| Problem | Solution |
|---------|----------|
| "GEMINI_API_KEY not set" | Edit `.env`, add your key |
| WebSocket won't connect | Check server is running on port 8000 |
| TTS fails | Either skip TTS or add GCP credentials |
| Import errors | Activate venv: `source venv/bin/activate` |

## What You Can Do Now

✅ NPCs respond with personality-driven dialogue  
✅ Context-aware (time, weather, reputation)  
✅ Persistent memory per NPC  
✅ Emotional responses (7 emotions)  
✅ Behavioral actions (approach, flee, attack, etc.)  
✅ Voice synthesis (TTS)  
✅ Streaming responses for UI  

## Next Steps

1. Customize NPC personas in Unity
2. Hook up animator triggers for emotions
3. Implement behavior directives
4. Add dialogue UI with typewriter effect
5. Test with different context scenarios

**Full docs:** [`README.md`](./README.md)  
**Unity guide:** [`unity/README.md`](./unity/README.md)

---

**Need help?** Check:
- API Docs: http://localhost:8000/docs
- Health: http://localhost:8000/healthz
- Logs: Check terminal output

🎮 **Happy building!**

