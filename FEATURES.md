# RPGAI Features & Capabilities

## 🎯 Core Features

### 1. **Intelligent NPC Dialogue** 🧠

NPCs generate contextual, personality-driven responses using Google's Gemini LLM:

```
Player: "Can you help me find the sacred grove?"

Elenor (Elven Mage, wise, formal):
→ "The sacred grove? Few dare venture there anymore. But given 
   your recent kindness in returning my ring, I sense you are 
   worthy. Head north past the Silverwoods."

Context considered:
✓ NPC personality (wise, formal)
✓ Past interactions (returned ring)
✓ Current scene (Silverwoods clearing)
✓ Player reputation (+12)
```

**Key Benefits:**
- No pre-scripted dialogue trees
- Every conversation feels unique
- NPCs remember past interactions
- Responses adapt to game state

---

### 2. **Structured JSON Output** 📋

Gemini is configured with a strict JSON Schema to ensure Unity ALWAYS receives valid, parseable data:

```json
{
  "utterance": "The sacred grove? Few dare venture...",
  "emotion": "neutral",
  "style_tags": ["formal", "mystical"],
  "behavior_directive": "none",
  "memory_writes": [
    {
      "salience": 1,
      "text": "Player asked about sacred grove"
    }
  ]
}
```

**Why this matters:**
- No more parsing errors or crashes
- Predictable data structure
- Type-safe Unity integration
- Automatic validation

---

### 3. **NPC Memory System** 💾

Each NPC maintains persistent memory of interactions with the player:

**Memory Storage:**
```sql
id | npc_id  | player_id | text                           | salience | ts
---+---------+-----------+--------------------------------+----------+----------
1  | elenor  | p1        | Player returned lost ring      | 2        | 16995648
2  | elenor  | p1        | Asked about sacred grove       | 1        | 16995660
3  | garrick | p1        | Player bought health potion    | 0        | 16995670
```

**Salience Levels:**
- **3 = Critical** (life-threatening events, major betrayals)
- **2 = Important** (significant kindness, quest completions)
- **1 = Notable** (casual conversations, minor events)
- **0 = Trivial** (greetings, weather comments)

**Retrieval Algorithm:**
```
Top-K Memories = ORDER BY (salience DESC, recency DESC) LIMIT 3
```

**Example Evolution:**
```
Turn 1: Player steals item
  Memory: "Player stole potion" (salience=3)
  Response: "How dare you! Guards!" (angry)

Turn 2: Player returns next day
  Retrieves: "Player stole potion" (salience=3)
  Response: "You! Get out!" (angry, step_back)

Turn 3: Player gives expensive gift
  Retrieves: "Player stole potion" (salience=3)
  New Memory: "Player gave gift as apology" (salience=2)
  Response: "Perhaps... I misjudged you." (neutral)
```

---

### 4. **WebSocket Streaming** ⚡

Real-time token streaming for smooth typewriter effects:

```
Client connects → ws://localhost:8000/v1/chat.stream
Client sends: {npc_id, player_text, persona, context}

Server streams:
{"type":"token", "text":"The "}
{"type":"token", "text":"sacred "}
{"type":"token", "text":"grove? "}
{"type":"token", "text":"Few "}
...
{"type":"final", "json":"{...complete_response...}"}
```

**Benefits:**
- Players see responses appear naturally
- No waiting for complete response
- Lower perceived latency
- More immersive experience

---

### 5. **Emotional AI** 😊😠😨

7 distinct emotions with automatic detection:

| Emotion | Triggers | Use Cases |
|---------|----------|-----------|
| **neutral** | Default | Calm conversation |
| **happy** | Kindness, gifts, quest completion | Warm greetings |
| **angry** | Theft, insults, betrayal | Hostile responses |
| **fear** | Threats, low health, danger | Fleeing, cowering |
| **sad** | Loss, bad news | Mourning, sympathy |
| **surprised** | Unexpected events | Shock, disbelief |
| **disgust** | Moral violations | Contempt, rejection |

**Unity Integration:**
```csharp
private void ApplyEmotion(Emotion emotion)
{
    // Trigger animation
    animator.SetTrigger(emotion.ToString());
    
    // Update facial expression
    faceController.SetExpression(emotion);
    
    // Play particle effect
    if (emotion == Emotion.angry)
        angerParticles.Play();
}
```

---

### 6. **Behavioral Directives** 🎬

10 action types that NPCs can trigger:

| Directive | Description | Example Trigger |
|-----------|-------------|-----------------|
| **none** | No action | Casual conversation |
| **approach** | Walk toward player | Friendly greeting, help offer |
| **step_back** | Retreat | Intimidation, fear |
| **flee** | Run away | Mortal danger, terror |
| **attack** | Initiate combat | Severe provocation |
| **call_guard** | Alert authorities | Crime witnessed |
| **give_item** | Hand item to player | Quest reward, gift |
| **start_quest** | Offer quest | Player proves worthy |
| **open_shop** | Show inventory | Merchant interaction |
| **heal_player** | Restore health | Healer NPC, kindness |

**Unity Behavior System:**
```csharp
private void ExecuteBehavior(BehaviorDirective directive)
{
    switch (directive)
    {
        case BehaviorDirective.approach:
            navAgent.SetDestination(player.position);
            break;
        
        case BehaviorDirective.call_guard:
            GuardSystem.AlertGuards(transform.position);
            reputation.Modify(-10);
            break;
        
        case BehaviorDirective.give_item:
            inventory.Transfer(questItem, player);
            break;
    }
}
```

---

### 7. **Voice Synthesis (TTS)** 🎙️

Google Cloud Text-to-Speech with emotional prosody:

**Voice Presets:**
```
feminine_calm   → en-US-Neural2-C   (default, measured)
feminine_young  → en-US-Neural2-F   (energetic, bright)
masculine_deep  → en-US-Neural2-D   (authoritative, gruff)
masculine_casual→ en-US-Neural2-A   (friendly, relaxed)
elderly_wise    → en-GB-Neural2-B   (weathered, sage)
```

**Emotional SSML:**
```xml
<!-- Angry -->
<speak>
  <prosody rate="105%" pitch="+2st" volume="loud">
    How dare you enter my shop after what you did!
  </prosody>
</speak>

<!-- Sad -->
<speak>
  <prosody rate="92%" pitch="-1st" volume="soft">
    She was... everything to me.
  </prosody>
</speak>
```

**Unity Playback:**
```csharp
await tts.PlayTTS(response.utterance, "en-US-Neural2-C");
```

---

### 8. **Voice Input (STT)** 🎤

Google Cloud Speech-to-Text for player voice input:

**Supported Formats:**
- WAV (Linear16, 16kHz recommended)
- MP3 (auto-detected)
- FLAC (lossless)
- OGG Opus (web-friendly)
- WEBM Opus (streaming)

**Features:**
- Automatic punctuation
- Confidence scoring
- Multi-language support
- Real-time transcription

**Unity Integration:**
```csharp
// Record from microphone
Microphone.Start(device, false, 10, 16000);

// Stop and convert
byte[] wavData = ConvertToWAV(samples, frequency, channels);

// Transcribe
WWWForm form = new WWWForm();
form.AddBinaryData("audio", wavData, "recording.wav");
var request = UnityWebRequest.Post(sttEndpoint, form);
await request.SendWebRequest();

// Get transcribed text
var response = JsonUtility.FromJson<STTResponse>(request.downloadHandler.text);
string playerText = response.text;

// Use in dialogue
await dialogue.SendPlayerMessage(npcId, playerText, persona);
```

**Complete Voice Workflow:**
1. Player holds "Talk" button → Record audio
2. Player releases button → Send to `/v1/voice/stt`
3. Server transcribes → Returns text
4. Unity sends text → Normal dialogue flow
5. NPC responds → TTS plays audio

**Unity Playback:**
```csharp
await ttsPlayer.PlayTTS(response.utterance, "en-US-Neural2-C");
```

---

### 9. **Context-Aware Dialogue** 🌍

NPCs adapt responses to dynamic game state:

**Context Fields:**
```json
{
  "scene": "tavern",
  "time_of_day": "midnight",
  "weather": "storm",
  "last_player_action": "saved_child",
  "player_reputation": 15,
  "npc_health": 100,
  "npc_alertness": 0.2
}
```

**Example Adaptations:**

**Weather:**
```
Clear day: "Perfect weather for travel!"
Storm: "You came out in this storm? You must need help urgently."
```

**Time of Day:**
```
Dawn: "Early riser, eh? I respect that."
Midnight: "What brings you here at this ungodly hour?"
```

**Reputation:**
```
Rep = -5: "I've heard about you. Keep your distance."
Rep = +15: "My friend! Always a pleasure to see you."
```

**NPC State:**
```
Health = 30: "I... I need a healer... quickly..."
Alertness = 0.9: "Who's there?! Show yourself!"
```

---

### 10. **Production-Ready Architecture** 🏗️

**FastAPI Backend:**
- Async/await for non-blocking I/O
- CORS middleware for Unity communication
- Structured logging with request IDs
- Health check endpoints
- Auto-generated API docs (`/docs`)
- Error handling with proper HTTP status codes

**Unity Client:**
- NativeWebSocket for cross-platform support (including WebGL)
- Async/await with UnityWebRequest
- Type-safe data models
- Event-driven architecture
- Graceful error handling

**Data Persistence:**
- SQLite for lightweight storage
- Indexed queries for fast retrieval
- Automatic schema creation
- Transaction safety
- Memory cleanup utilities

---

### 10. **Developer Experience** 🛠️

**Comprehensive Documentation:**
- ✓ README with full API reference
- ✓ QUICKSTART for 5-minute setup
- ✓ Unity integration guide
- ✓ Project structure overview
- ✓ Troubleshooting guide

**Testing Suite:**
- ✓ Unit tests for memory system
- ✓ Schema validation tests
- ✓ Sample outputs tested
- ✓ Edge case coverage

**Easy Setup:**
```bash
./setup.sh              # Automated setup
source venv/bin/activate
uvicorn server.main:app --reload
```

**Interactive API Docs:**
```
http://localhost:8000/docs
→ Try all endpoints directly in browser
→ Auto-generated from Pydantic models
→ Request/response examples
```

---

## 🎮 Use Cases

### Medieval Fantasy RPG
```
NPC: Village Elder
Personality: Wise, cautious, protective
Memory: Remembers if player helped during goblin raid
Context: Time of day affects availability
Behavior: Offers quests if player has good reputation
```

### Sci-Fi Space Station
```
NPC: Station Commander
Personality: Military, direct, suspicious
Memory: Tracks security clearance violations
Context: Station alert level affects responses
Behavior: Can lock down areas or call security
```

### Modern Detective Game
```
NPC: Witness
Personality: Nervous, evasive, secretive
Memory: Contradicts self if questioned twice
Context: Presence of police affects honesty
Behavior: Can flee if pressured too much
```

---

## 📊 Technical Specifications

**Backend:**
- Language: Python 3.9+
- Framework: FastAPI
- LLM: Google Gemini (gemini-2.0-flash-exp)
- TTS: Google Cloud Text-to-Speech
- STT: Google Cloud Speech-to-Text
- Database: SQLite 3
- Transport: WebSocket + HTTP

**Unity:**
- Version: 2021.3 LTS+
- Language: C# 9.0
- WebSocket: NativeWebSocket
- HTTP: UnityWebRequest
- Audio: AudioSource (MP3)

**Performance:**
- Average response time: 1-3 seconds
- Memory per NPC: ~100 KB
- Concurrent connections: 100+ (configurable)
- Token streaming latency: <100ms

---

## 🚀 Future Enhancements

**Planned Features:**
- [x] Voice input (speech-to-text) - **IMPLEMENTED**
- [ ] Multi-language support
- [ ] NPC-to-NPC conversations
- [ ] Long-term memory (days/weeks)
- [ ] Personality evolution
- [ ] Quest generation
- [ ] World knowledge base
- [ ] Facial animation integration
- [ ] Gesture recognition
- [ ] Group conversations

**Stretch Goals:**
- [ ] Redis caching for distributed memory
- [ ] Fine-tuned character models
- [ ] Real-time lip sync
- [ ] Procedural quest generation
- [ ] Dynamic relationship graphs
- [ ] Emotion blending
- [ ] Context prediction

---

## 💡 Innovation Highlights

**What makes RPGAI unique:**

1. **Guaranteed Valid Output** - JSON Schema enforcement prevents parsing errors
2. **Salience-Based Memory** - Important events naturally surface in context
3. **Streaming for UX** - Typewriter effect feels more natural than waiting
4. **Emotion-Driven TTS** - Speech prosody matches NPC emotional state
5. **Voice Input Support** - Full speech-to-text integration for natural conversations
6. **Zero Dialogue Trees** - Completely generative, no pre-written scripts
7. **Context Integration** - Weather, time, reputation all affect responses
8. **Production Architecture** - Not a proof-of-concept, ready to deploy

---

**Built for immersive RPG experiences. Every conversation tells a story.**

🎮 **Ready to bring your NPCs to life?** See [`QUICKSTART.md`](./QUICKSTART.md)

