#!/usr/bin/env python3
"""
End-to-end test: Voice Input → Dialogue → Voice Output
Tests the complete voice dialogue flow:
1. STT: Audio → Text
2. Chat: Text → NPC Response
3. TTS: NPC Response → Audio
"""

import asyncio
import json
import requests
import websockets
from pathlib import Path

# Configuration
BASE_URL = "http://localhost:8000"
WS_URL = "ws://localhost:8000/v1/chat.stream"
AUDIO_FILE = "/Users/yashas/Desktop/RPGAI/audio_file.wav"  # Your recorded audio file

# Test NPC persona
NPC_PERSONA = {
    "name": "Elenor",
    "role": "Elven mage",
    "values": ["wisdom", "order", "loyalty"],
    "quirks": ["formal", "measured"],
    "backstory": ["lives in Silverwoods", "distrusts smugglers"]
}

# Test game context
GAME_CONTEXT = {
    "scene": "Silverwoods_clearing",
    "time_of_day": "afternoon",
    "weather": "clear",
    "last_player_action": None,
    "player_reputation": 0,
    "npc_health": 100,
    "npc_alertness": 0.0
}


def step1_stt(audio_file: str) -> str:
    """Step 1: Transcribe audio to text"""
    print("\n" + "="*60)
    print("STEP 1: Speech-to-Text (STT)")
    print("="*60)
    
    if not Path(audio_file).exists():
        raise FileNotFoundError(f"Audio file not found: {audio_file}")
    
    print(f"📤 Sending audio file: {audio_file}")
    
    with open(audio_file, "rb") as f:
        files = {"audio": (audio_file, f, "audio/wav")}
        data = {"language_code": "en-US"}
        
        response = requests.post(
            f"{BASE_URL}/v1/voice/stt",
            files=files,
            data=data
        )
    
    if response.status_code != 200:
        print(f"❌ STT failed: {response.status_code}")
        print(response.text)
        raise Exception(f"STT failed: {response.text}")
    
    result = response.json()
    transcribed_text = result["text"]
    confidence = result.get("confidence", "N/A")
    
    print(f"✅ Transcription successful!")
    print(f"   Text: '{transcribed_text}'")
    print(f"   Confidence: {confidence}")
    
    return transcribed_text


async def step2_chat(player_text: str) -> dict:
    """Step 2: Get NPC dialogue response"""
    print("\n" + "="*60)
    print("STEP 2: NPC Dialogue (WebSocket)")
    print("="*60)
    
    print(f"📤 Sending player text: '{player_text}'")
    
    # Build chat turn request
    payload = {
        "npc_id": "elenor",
        "player_id": "test_player",
        "player_text": player_text,
        "persona": NPC_PERSONA,
        "context": GAME_CONTEXT
    }
    
    print("🔌 Connecting to WebSocket...")
    
    async with websockets.connect(WS_URL) as websocket:
        # Send the request
        await websocket.send(json.dumps(payload))
        print("📤 Request sent, waiting for response...")
        
        # Collect streaming tokens
        tokens = []
        final_json = None
        
        async for message in websocket:
            data = json.loads(message)
            
            if data["type"] == "token":
                tokens.append(data["text"])
                print(f"   Token: {data['text']}", end="", flush=True)
            
            elif data["type"] == "final":
                final_json = json.loads(data["json"])
                print("\n✅ Response complete!")
                break
            
            elif data["type"] == "error":
                print(f"\n❌ Error: {data['message']}")
                raise Exception(f"Chat error: {data['message']}")
        
        # Print full response
        full_text = "".join(tokens)
        print(f"\n   Full text: '{full_text}'")
        print(f"   Emotion: {final_json.get('emotion', 'N/A')}")
        print(f"   Behavior: {final_json.get('behavior_directive', 'N/A')}")
        
        return final_json


def step3_tts(npc_response: dict) -> str:
    """Step 3: Synthesize NPC response to audio"""
    print("\n" + "="*60)
    print("STEP 3: Text-to-Speech (TTS)")
    print("="*60)
    
    utterance = npc_response["utterance"]
    emotion = npc_response.get("emotion", "neutral")
    
    # Build SSML with emotion
    ssml = f"<speak><prosody rate='100%'>{utterance}</prosody></speak>"
    
    print(f"📤 Synthesizing: '{utterance}'")
    print(f"   Emotion: {emotion}")
    
    payload = {
        "ssml": ssml,
        "voice_name": "en-US-Neural2-C"
    }
    
    response = requests.post(
        f"{BASE_URL}/v1/voice/tts",
        json=payload
    )
    
    if response.status_code != 200:
        print(f"❌ TTS failed: {response.status_code}")
        print(response.text)
        raise Exception(f"TTS failed: {response.text}")
    
    result = response.json()
    audio_url = result["audio_url"]
    
    print(f"✅ Audio generated!")
    print(f"   URL: {audio_url}")
    
    # Download the audio file
    audio_response = requests.get(audio_url)
    output_file = "npc_response.mp3"
    with open(output_file, "wb") as f:
        f.write(audio_response.content)
    
    print(f"💾 Saved to: {output_file}")
    
    return audio_url, output_file


async def main():
    """Run complete end-to-end test"""
    print("\n" + "="*60)
    print("🎮 END-TO-END VOICE DIALOGUE TEST")
    print("="*60)
    print(f"Audio file: {AUDIO_FILE}")
    print(f"Server: {BASE_URL}")
    
    try:
        # Step 1: STT
        player_text = step1_stt(AUDIO_FILE)
        
        # Step 2: Chat
        npc_response = await step2_chat(player_text)
        
        # Step 3: TTS
        audio_url, audio_file = step3_tts(npc_response)
        
        # Summary
        print("\n" + "="*60)
        print("✅ END-TO-END TEST COMPLETE!")
        print("="*60)
        print(f"📝 Player said: '{player_text}'")
        print(f"💬 NPC replied: '{npc_response['utterance']}'")
        print(f"🎵 Audio saved: {audio_file}")
        print(f"🔗 Audio URL: {audio_url}")
        print("\n🎉 You can now play the audio file to hear the NPC response!")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())