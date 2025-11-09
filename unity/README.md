# Unity Integration Guide

## Prerequisites

1. **Unity 2021.3 LTS or newer**
2. **NativeWebSocket package** for WebSocket support

## Installation

### 1. Install NativeWebSocket

Open Unity Package Manager (`Window` > `Package Manager`), click the `+` button, and select `Add package from git URL`:

```
https://github.com/endel/NativeWebSocket.git#upm
```

### 2. Copy Scripts

Copy all scripts from `Assets/Scripts/` into your Unity project's `Assets/Scripts/` folder.

### 3. Setup Scene

#### Create Dialogue System GameObject

1. Create empty GameObject: `DialogueSystem`
2. Add `DialogueController` component
3. Add `GameContextProvider` component
4. Set **Server URL** in DialogueController: `ws://localhost:8000/v1/chat.stream`

#### Create TTS Player GameObject

1. Create empty GameObject: `TTSPlayer`
2. Add `AudioSource` component
3. Add `TTSPlayer` component
4. Set **TTS Endpoint**: `http://localhost:8000/v1/voice/tts`

#### Wire References

In `DialogueController`:
- Assign `GameContextProvider` reference

### 4. Backend Server

Make sure the Python backend is running:

```bash
cd ../
uvicorn server.main:app --reload --port 8000
```

## Usage Example

### Basic Dialogue

```csharp
using RPGAI.Dialogue;
using UnityEngine;

public class NpcInteraction : MonoBehaviour
{
    [SerializeField] private DialogueController dialogue;
    
    private NpcPersona elenor = new NpcPersona
    {
        name = "Elenor",
        role = "Elven mage",
        values = new[] { "wisdom", "order", "loyalty" },
        quirks = new[] { "formal", "measured" },
        backstory = new[] { "lives in Silverwoods", "distrusts smugglers" }
    };
    
    private void Start()
    {
        dialogue.OnTokenReceived += OnDialogueToken;
        dialogue.OnResponseComplete += OnDialogueComplete;
    }
    
    public async void TalkToElenor(string playerText)
    {
        await dialogue.SendPlayerMessage("elenor", playerText, elenor);
    }
    
    private void OnDialogueToken(string token)
    {
        // Show token in UI (typewriter effect)
        Debug.Log($"Token: {token}");
    }
    
    private void OnDialogueComplete(NpcResponse response)
    {
        Debug.Log($"NPC says: {response.utterance}");
        Debug.Log($"Emotion: {response.emotion}");
        
        // Apply to your systems
        ApplyEmotion(response.emotion);
        ExecuteBehavior(response.behavior_directive);
    }
}
```

### With TTS

```csharp
using RPGAI.Audio;
using RPGAI.Dialogue;

public class DialogueWithVoice : MonoBehaviour
{
    [SerializeField] private DialogueController dialogue;
    [SerializeField] private TTSPlayer tts;
    
    private void Start()
    {
        dialogue.OnResponseComplete += async (response) =>
        {
            // Play the utterance as speech
            await tts.PlayTTS(response.utterance, "en-US-Neural2-C");
            
            // Or with voice hint from response
            if (response.voice_hint != null)
            {
                string voice = GetVoiceFromPreset(response.voice_hint.voice_preset);
                await tts.PlayTTS(response.utterance, voice);
            }
        };
    }
    
    private string GetVoiceFromPreset(string preset)
    {
        return preset switch
        {
            "feminine_calm" => "en-US-Neural2-C",
            "masculine_deep" => "en-US-Neural2-D",
            _ => "en-US-Neural2-C"
        };
    }
}
```

### With Voice Input (Speech-to-Text)

```csharp
using RPGAI.Audio;
using RPGAI.Dialogue;
using RPGAI.Net;
using UnityEngine;
using System.Threading.Tasks;

public class VoiceInputDialogue : MonoBehaviour
{
    [SerializeField] private DialogueController dialogue;
    [SerializeField] private string sttEndpoint = "http://localhost:8000/v1/voice/stt";
    
    private AudioClip recordedClip;
    private string microphoneDevice;
    
    private void Start()
    {
        // Get default microphone
        if (Microphone.devices.Length > 0)
        {
            microphoneDevice = Microphone.devices[0];
            Debug.Log($"Using microphone: {microphoneDevice}");
        }
    }
    
    // Call this when player presses "talk" button
    public void StartRecording()
    {
        if (string.IsNullOrEmpty(microphoneDevice))
        {
            Debug.LogError("No microphone detected");
            return;
        }
        
        // Record for up to 10 seconds at 16kHz
        recordedClip = Microphone.Start(microphoneDevice, false, 10, 16000);
        Debug.Log("Recording started...");
    }
    
    // Call this when player releases "talk" button
    public async Task StopRecordingAndSend(string npcId, NpcPersona persona)
    {
        if (!Microphone.IsRecording(microphoneDevice))
        {
            Debug.LogWarning("Not recording");
            return;
        }
        
        int position = Microphone.GetPosition(microphoneDevice);
        Microphone.End(microphoneDevice);
        
        Debug.Log("Recording stopped");
        
        // Trim the audio clip to actual recorded length
        float[] samples = new float[position * recordedClip.channels];
        recordedClip.GetData(samples, 0);
        
        // Convert to WAV bytes
        byte[] wavData = ConvertToWAV(samples, recordedClip.frequency, recordedClip.channels);
        
        // Send to STT endpoint
        string transcribedText = await TranscribeAudio(wavData);
        
        if (!string.IsNullOrEmpty(transcribedText))
        {
            Debug.Log($"Player said: {transcribedText}");
            
            // Send transcribed text to dialogue system
            await dialogue.SendPlayerMessage(npcId, transcribedText, persona);
        }
    }
    
    private async Task<string> TranscribeAudio(byte[] audioData)
    {
        try
        {
            // Create multipart form data
            WWWForm form = new WWWForm();
            form.AddBinaryData("audio", audioData, "recording.wav", "audio/wav");
            form.AddField("language_code", "en-US");
            
            using (var request = UnityWebRequest.Post(sttEndpoint, form))
            {
                var operation = request.SendWebRequest();
                
                while (!operation.isDone)
                {
                    await Task.Yield();
                }
                
                if (request.result != UnityWebRequest.Result.Success)
                {
                    Debug.LogError($"STT request failed: {request.error}");
                    return null;
                }
                
                // Parse response
                var response = JsonUtility.FromJson<STTResponse>(request.downloadHandler.text);
                return response.text;
            }
        }
        catch (System.Exception e)
        {
            Debug.LogError($"STT error: {e.Message}");
            return null;
        }
    }
    
    private byte[] ConvertToWAV(float[] samples, int frequency, int channels)
    {
        // Simple WAV file conversion
        int sampleCount = samples.Length;
        int byteCount = sampleCount * 2; // 16-bit samples
        
        using (var memoryStream = new System.IO.MemoryStream())
        using (var writer = new System.IO.BinaryWriter(memoryStream))
        {
            // WAV header
            writer.Write(new char[4] { 'R', 'I', 'F', 'F' });
            writer.Write(36 + byteCount);
            writer.Write(new char[4] { 'W', 'A', 'V', 'E' });
            writer.Write(new char[4] { 'f', 'm', 't', ' ' });
            writer.Write(16); // Subchunk1Size
            writer.Write((ushort)1); // AudioFormat (PCM)
            writer.Write((ushort)channels);
            writer.Write(frequency);
            writer.Write(frequency * channels * 2); // ByteRate
            writer.Write((ushort)(channels * 2)); // BlockAlign
            writer.Write((ushort)16); // BitsPerSample
            writer.Write(new char[4] { 'd', 'a', 't', 'a' });
            writer.Write(byteCount);
            
            // Write samples
            foreach (float sample in samples)
            {
                short intSample = (short)(sample * short.MaxValue);
                writer.Write(intSample);
            }
            
            return memoryStream.ToArray();
        }
    }
    
    [System.Serializable]
    private class STTResponse
    {
        public string text;
        public float confidence;
    }
}
```

### Context Integration

```csharp
using RPGAI.State;
using UnityEngine;

public class GameManager : MonoBehaviour
{
    [SerializeField] private GameContextProvider contextProvider;
    
    private void Update()
    {
        // Update time of day
        float timeOfDay = Time.time % 86400f;
        if (timeOfDay < 21600) contextProvider.SetTimeOfDay("night");
        else if (timeOfDay < 43200) contextProvider.SetTimeOfDay("morning");
        else if (timeOfDay < 64800) contextProvider.SetTimeOfDay("afternoon");
        else contextProvider.SetTimeOfDay("evening");
    }
    
    public void OnPlayerAction(string action)
    {
        contextProvider.SetLastPlayerAction(action);
        
        // Adjust reputation based on action
        if (action == "helped_npc") contextProvider.ModifyReputation(2);
        if (action == "stole_item") contextProvider.ModifyReputation(-5);
    }
    
    public void OnWeatherChange(string weather)
    {
        contextProvider.SetWeather(weather);
    }
}
```

### Memory Management

Write memories from gameplay events:

```csharp
using RPGAI.Net;
using System.Threading.Tasks;

public async Task WriteMemory(string npcId, string playerId, string text, int salience)
{
    var payload = new
    {
        npc_id = npcId,
        player_id = playerId,
        text = text,
        salience = salience,
        keys = new[] { "quest", "item" },
        @private = true
    };
    
    string json = JsonUtility.ToJson(payload);
    await HttpClient.PostJson("http://localhost:8000/v1/memory/write", json);
}

// Example: Player completes quest
await WriteMemory("elenor", "p1", "Player completed arcane trial", 2);
```

## Response Schema

The `NpcResponse` contains:

```csharp
public class NpcResponse
{
    public string utterance;                    // What NPC says
    public Emotion emotion;                     // neutral|happy|angry|fear|sad|surprised|disgust
    public string[] style_tags;                 // Optional: ["formal", "whisper"]
    public BehaviorDirective behavior_directive; // Action to execute
    public MemoryWrite[] memory_writes;         // Memories to persist
    public PublicEvent[] public_events;         // World events
    public VoiceHint voice_hint;                // TTS configuration
}
```

## Applying Behaviors

```csharp
private void ExecuteBehavior(BehaviorDirective behavior)
{
    switch (behavior)
    {
        case BehaviorDirective.approach:
            npcAnimator.SetTrigger("Walk");
            npcAgent.SetDestination(player.position);
            break;
            
        case BehaviorDirective.step_back:
            Vector3 awayPos = transform.position - (player.position - transform.position);
            npcAgent.SetDestination(awayPos);
            break;
            
        case BehaviorDirective.attack:
            npcCombat.AttackTarget(player);
            break;
            
        case BehaviorDirective.call_guard:
            GuardSystem.AlertGuards(transform.position);
            break;
            
        case BehaviorDirective.give_item:
            inventory.GiveItem(player, questItem);
            break;
            
        case BehaviorDirective.open_shop:
            shopUI.Open(npcShop);
            break;
    }
}
```

## Applying Emotions

```csharp
private void ApplyEmotion(Emotion emotion)
{
    // Animator triggers
    npcAnimator.SetTrigger(emotion.ToString());
    
    // Particle effects
    if (emotion == Emotion.angry) 
        angryParticles.Play();
    
    // UI indicators
    emotionIcon.sprite = emotionSprites[(int)emotion];
}
```

## Troubleshooting

### WebSocket won't connect
- Check backend is running on `http://localhost:8000`
- Check firewall allows WebSocket connections
- Try HTTP first: `http://localhost:8000/healthz`

### NativeWebSocket errors
- Make sure package is installed via UPM
- For WebGL builds, WebSockets work differently (no `DispatchMessages` needed)

### JSON parsing errors
- Check Unity's JSON serializer limitations
- Use `[Serializable]` attribute on all data classes
- Avoid complex nested objects

### Audio won't play
- Check AudioSource is enabled
- Verify backend TTS endpoint is reachable
- Check GCP credentials are configured on backend

### Voice input (STT) not working
- Check microphone permissions on mobile (see Platform Notes)
- Verify backend STT endpoint is reachable: `http://localhost:8000/v1/voice/stt`
- Ensure GCP Speech-to-Text API is enabled in your GCP project
- Check audio format is supported (WAV, MP3, FLAC, OGG, WEBM)
- Verify microphone is detected: `Microphone.devices` should not be empty

## Platform Notes

### WebGL
- WebSockets work natively (browser handles them)
- Don't call `DispatchMessages()` on WebGL
- Audio streaming may have CORS issues (serve from same domain)
- Microphone access requires HTTPS and user permission

### Mobile (iOS/Android)
- Use HTTPS/WSS for production (not HTTP/WS)
- **Microphone permissions required for STT:**
  - iOS: Add `NSMicrophoneUsageDescription` to Info.plist
  - Android: Add `<uses-permission android:name="android.permission.RECORD_AUDIO"/>` to AndroidManifest.xml
  - Request permissions at runtime: `Application.RequestUserAuthorization(UserAuthorization.Microphone)`
- Test TTS audio formats (MP3 works on most platforms)

### Desktop
- Works out of the box
- Consider firewall rules for WebSocket connections

## Performance Tips

1. **Throttle context updates** - Don't send every frame's state change
2. **Reuse WebSocket** - Keep connection alive between turns
3. **Cache personas** - Create NPC personas once, reuse them
4. **Async/await** - All network calls are async to avoid blocking game thread
5. **Object pooling** - For UI text elements in dialogue boxes

## Next Steps

- Add UI for dialogue display (TextMeshPro recommended)
- Integrate with quest system via `public_events`
- Add character portraits with emotion sprites
- Implement camera focus during conversations
- Add subtitle display for accessibility
- Create dialogue history panel

---

For backend documentation, see `../README.md`

