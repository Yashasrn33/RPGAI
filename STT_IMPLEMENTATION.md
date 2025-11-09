# Speech-to-Text Implementation Summary

## Overview

Implemented server-side Speech-to-Text (STT) using Google Cloud Platform's Speech-to-Text API. This allows players to use voice input for dialogue instead of text.

## What Was Implemented

### 1. Backend Components

#### New Files:
- **`server/stt.py`** - Speech-to-Text client module
  - `STTClient` class for transcribing audio
  - Support for multiple audio formats (WAV, MP3, FLAC, OGG, WEBM)
  - Automatic sample rate detection
  - Confidence scoring

#### Modified Files:
- **`server/requirements.txt`**
  - Added: `google-cloud-speech==2.26.0`

- **`server/schemas.py`**
  - Added: `STTRequest` model
  - Added: `STTResponse` model with text and confidence fields

- **`server/main.py`**
  - Added: `POST /v1/voice/stt` endpoint
  - Accepts multipart/form-data with audio file
  - Returns transcribed text

### 2. Documentation

#### Updated Files:
- **`unity/README.md`**
  - Added complete voice input example with microphone recording
  - Added WAV conversion utility
  - Added troubleshooting section for STT
  - Added platform-specific microphone permission notes

- **`README.md`**
  - Updated prerequisites to mention Speech-to-Text API
  - Added STT API documentation with curl examples
  - Added workflow description for voice input
  - Updated GCP setup section

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Unity (Player)                          │
│                                                              │
│  1. Microphone.Start() → Record audio                       │
│  2. Convert to WAV format                                   │
│  3. POST /v1/voice/stt (multipart form)                    │
│     ↓                                                        │
└─────┼────────────────────────────────────────────────────────┘
      │
      │ HTTP POST (audio file)
      ↓
┌─────────────────────────────────────────────────────────────┐
│                   FastAPI Backend                            │
│                                                              │
│  1. Receive audio file                                      │
│  2. stt.py: transcribe_audio()                             │
│  3. Google Cloud Speech-to-Text API                        │
│     ↓                                                        │
│  4. Return: {"text": "...", "confidence": 0.95}           │
└─────┼────────────────────────────────────────────────────────┘
      │
      │ JSON response
      ↓
┌─────────────────────────────────────────────────────────────┐
│                      Unity (Player)                          │
│                                                              │
│  1. Receive transcribed text                                │
│  2. Use text as player_text in ChatTurnRequest             │
│  3. Send via WebSocket to /v1/chat.stream                  │
└─────────────────────────────────────────────────────────────┘
```

## API Endpoint

### POST /v1/voice/stt

**Request:**
- Content-Type: `multipart/form-data`
- Fields:
  - `audio`: Audio file (WAV, MP3, FLAC, OGG, WEBM)
  - `language_code`: Language code (default: "en-US")

**Response:**
```json
{
  "text": "Hello, I would like to buy some potions",
  "confidence": 0.95
}
```

**Example (curl):**
```bash
curl -X POST http://localhost:8000/v1/voice/stt \
  -F "audio=@recording.wav" \
  -F "language_code=en-US"
```

## Unity Integration Example

```csharp
// 1. Start recording
Microphone.Start(deviceName, false, 10, 16000);

// 2. Stop and get audio data
int position = Microphone.GetPosition(deviceName);
Microphone.End(deviceName);
float[] samples = new float[position * channels];
recordedClip.GetData(samples, 0);

// 3. Convert to WAV
byte[] wavData = ConvertToWAV(samples, frequency, channels);

// 4. Send to STT endpoint
WWWForm form = new WWWForm();
form.AddBinaryData("audio", wavData, "recording.wav", "audio/wav");
form.AddField("language_code", "en-US");

using (var request = UnityWebRequest.Post(sttEndpoint, form))
{
    await request.SendWebRequest();
    var response = JsonUtility.FromJson<STTResponse>(request.downloadHandler.text);
    string transcribedText = response.text;
    
    // 5. Use in dialogue
    await dialogue.SendPlayerMessage(npcId, transcribedText, persona);
}
```

## Setup Requirements

### 1. Enable GCP Speech-to-Text API

```bash
gcloud services enable speech.googleapis.com
```

### 2. Install Dependencies

```bash
pip install -r server/requirements.txt
```

### 3. Verify GCP Credentials

Ensure `GOOGLE_APPLICATION_CREDENTIALS` environment variable points to your service account JSON key.

### 4. Mobile Permissions (Unity)

**iOS:** Add to Info.plist:
```xml
<key>NSMicrophoneUsageDescription</key>
<string>This app needs microphone access for voice chat with NPCs</string>
```

**Android:** Add to AndroidManifest.xml:
```xml
<uses-permission android:name="android.permission.RECORD_AUDIO"/>
```

**Runtime Permission:**
```csharp
await Application.RequestUserAuthorization(UserAuthorization.Microphone);
```

## Audio Format Support

The STT implementation supports multiple audio formats:

| Format | Encoding | Notes |
|--------|----------|-------|
| WAV | LINEAR16 | Requires sample rate specification (16kHz recommended) |
| MP3 | MP3 | Auto-detected sample rate |
| FLAC | FLAC | Auto-detected sample rate |
| OGG | OGG_OPUS | Auto-detected sample rate |
| WEBM | WEBM_OPUS | Auto-detected sample rate, good for web |

## Key Features

1. **Multi-format Support** - WAV, MP3, FLAC, OGG, WEBM
2. **Automatic Punctuation** - GCP adds punctuation to transcriptions
3. **Confidence Scoring** - Returns confidence level of transcription
4. **Language Support** - Configurable language code (defaults to en-US)
5. **Error Handling** - Comprehensive error handling and logging
6. **Platform Compatibility** - Works across desktop, mobile, and WebGL

## Testing

### Test STT Endpoint

1. Record a test audio file:
```bash
# macOS/Linux
ffmpeg -f avfoundation -i ":0" -t 5 recording.wav

# Windows
ffmpeg -f dshow -i audio="Microphone" -t 5 recording.wav
```

2. Send to endpoint:
```bash
curl -X POST http://localhost:8000/v1/voice/stt \
  -F "audio=@recording.wav" \
  -F "language_code=en-US"
```

3. Verify response:
```json
{
  "text": "your transcribed speech here",
  "confidence": 0.95
}
```

## Workflow: Voice-Based Dialogue

1. **Player presses "Talk" button** → Start recording
2. **Player speaks** → Audio captured via microphone
3. **Player releases button** → Stop recording
4. **Unity converts to WAV** → Prepare for upload
5. **Unity sends to /v1/voice/stt** → Transcribe audio
6. **Server returns text** → Transcribed player dialogue
7. **Unity uses text in ChatTurnRequest** → Normal dialogue flow
8. **Server generates NPC response** → Stream tokens via WebSocket
9. **Unity plays TTS audio** → NPC speaks response

## Benefits of Server-Side STT

1. **Consistent Experience** - Same accuracy across all platforms
2. **Centralized Updates** - Update STT logic without Unity rebuilds
3. **No Unity Dependencies** - No additional Unity packages required
4. **Reuses Existing GCP** - Leverages existing GCP integration
5. **Better Accuracy** - GCP's models are highly accurate
6. **Multi-language Support** - Easy to add language switching

## Future Enhancements

Potential improvements:
- [ ] Streaming STT for real-time transcription
- [ ] Language auto-detection
- [ ] Custom vocabulary/hints for RPG terms
- [ ] Profanity filtering
- [ ] Voice activity detection (VAD)
- [ ] Multiple speaker identification
- [ ] Dialect/accent support

## Troubleshooting

### "STT client not initialized"
- Check GCP credentials are set correctly
- Verify Speech-to-Text API is enabled in GCP console

### "No transcription results returned"
- Audio may be too quiet or empty
- Check audio format is supported
- Verify sample rate for WAV files (16kHz recommended)

### "Permission denied" on mobile
- Check microphone permissions are requested at runtime
- Verify platform-specific manifest entries

### "Empty audio file"
- Ensure audio data is not empty before sending
- Check microphone is recording successfully

## References

- [Google Cloud Speech-to-Text Docs](https://cloud.google.com/speech-to-text/docs)
- [Unity Microphone API](https://docs.unity3d.com/ScriptReference/Microphone.html)
- [FastAPI File Uploads](https://fastapi.tiangolo.com/tutorial/request-files/)

---

**Implementation Date:** November 9, 2025
**Version:** 1.0.0

