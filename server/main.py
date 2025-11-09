"""
RPGAI FastAPI Application
Main server for Unity NPC dialogue system with Gemini and Google Cloud TTS.
"""
import json
import logging
import time
from contextlib import asynccontextmanager
from typing import Dict, Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from pathlib import Path

from .schemas import (
    ChatTurnRequest,
    NpcMemoryWrite,
    TTSRequest,
    TTSResponse,
    MemoryEntry
)
from .memory import memory_dao
from .llm_client import generate_npc_json_stream
from .tts import synthesize_ssml
from .settings import settings

# Configure logging
logging.basicConfig(
    level=settings.log_level,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    logger.info("🚀 RPGAI server starting up...")
    logger.info(f"   Model: {settings.gemini_model}")
    logger.info(f"   Database: {settings.db_path}")
    logger.info(f"   Media directory: {settings.media_dir}")
    
    # Ensure media directory exists and is served
    media_path = Path(settings.media_dir)
    media_path.mkdir(parents=True, exist_ok=True)
    
    yield
    
    logger.info("🛑 RPGAI server shutting down...")


# Initialize FastAPI app
app = FastAPI(
    title="RPGAI - NPC Dialogue Service",
    description="LLM-powered NPC dialogue with memory and TTS for Unity",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware - allow all origins for demo (restrict in production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify Unity's domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve media files (generated audio)
media_path = Path(settings.media_dir)
media_path.mkdir(parents=True, exist_ok=True)
app.mount("/media", StaticFiles(directory=str(media_path)), name="media")


# ============================================================================
# WEBSOCKET: STREAMING CHAT
# ============================================================================

@app.websocket("/v1/chat.stream")
async def chat_stream(websocket: WebSocket):
    """
    WebSocket endpoint for streaming NPC dialogue.
    
    Flow:
    1. Client connects and sends one ChatTurnRequest JSON
    2. Server retrieves relevant memories
    3. Server streams tokens: {"type":"token", "text":"..."}
    4. Server sends final: {"type":"final", "json":"{...}"}
    
    The final JSON is a validated NpcDialogueResponse.
    """
    await websocket.accept()
    logger.info("WebSocket connection established")
    
    try:
        # Receive the turn payload
        start_time = time.time()
        data = await websocket.receive_json()
        
        try:
            payload = ChatTurnRequest(**data)
        except Exception as e:
            error_msg = {"type": "error", "message": f"Invalid payload: {str(e)}"}
            await websocket.send_json(error_msg)
            await websocket.close()
            return
        
        logger.info(
            f"Received chat turn: npc={payload.npc_id}, "
            f"player={payload.player_id}, text='{payload.player_text[:50]}...'"
        )
        
        # Retrieve relevant memories (top 3 by salience & recency)
        memories = memory_dao.top(
            npc_id=payload.npc_id,
            player_id=payload.player_id,
            k=3,
            min_salience=0
        )
        logger.info(f"Retrieved {len(memories)} memories")
        
        # Stream the response
        token_count = 0
        async for chunk in generate_npc_json_stream(payload, memories):
            await websocket.send_json(chunk)
            
            if chunk["type"] == "token":
                token_count += 1
            elif chunk["type"] == "final":
                # Parse the final JSON to extract memory_writes
                try:
                    final_response = json.loads(chunk["json"])
                    
                    # Auto-write memories if the model generated any
                    if "memory_writes" in final_response and final_response["memory_writes"]:
                        for mem_write in final_response["memory_writes"]:
                            memory_dao.write(
                                npc_id=payload.npc_id,
                                player_id=payload.player_id,
                                text=mem_write["text"],
                                salience=mem_write["salience"],
                                private=mem_write.get("private", True),
                                keys=mem_write.get("keys", None)
                            )
                        logger.info(f"Auto-wrote {len(final_response['memory_writes'])} memories")
                except Exception as e:
                    logger.error(f"Error processing memory_writes: {e}")
        
        elapsed = time.time() - start_time
        logger.info(
            f"Turn completed: {token_count} tokens streamed, "
            f"elapsed={elapsed:.2f}s"
        )
    
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected by client")
    except Exception as e:
        logger.error(f"WebSocket error: {e}", exc_info=True)
        try:
            error_msg = {"type": "error", "message": str(e)}
            await websocket.send_json(error_msg)
        except:
            pass
    finally:
        try:
            await websocket.close()
        except:
            pass


# ============================================================================
# HTTP: MEMORY MANAGEMENT
# ============================================================================

@app.post("/v1/memory/write", status_code=status.HTTP_201_CREATED)
async def write_memory(memory: NpcMemoryWrite) -> Dict[str, Any]:
    """
    Write a memory entry.
    
    Request body:
    {
        "npc_id": "elenor",
        "player_id": "p1",
        "text": "Player returned lost ring",
        "salience": 2,
        "keys": ["ring", "kind_deed"],
        "private": true
    }
    """
    try:
        row_id = memory_dao.write_from_model(memory)
        logger.info(f"Memory written: id={row_id}, npc={memory.npc_id}")
        return {"ok": True, "id": row_id}
    except Exception as e:
        logger.error(f"Error writing memory: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@app.get("/v1/memory/top")
async def get_top_memories(
    npc_id: str,
    player_id: str,
    k: int = 3
) -> Dict[str, Any]:
    """
    Retrieve top-k memories ordered by salience and recency.
    
    Query params:
    - npc_id: NPC identifier
    - player_id: Player identifier
    - k: Number of memories to retrieve (default 3)
    
    Returns:
    {
        "memories": [
            {
                "id": 1,
                "npc_id": "elenor",
                "player_id": "p1",
                "text": "Player returned lost ring",
                "salience": 2,
                "private": true,
                "keys": "[\"ring\", \"kind_deed\"]",
                "ts": 1699564800
            }
        ]
    }
    """
    try:
        memories = memory_dao.top(npc_id, player_id, k)
        return {
            "memories": [mem.model_dump() for mem in memories]
        }
    except Exception as e:
        logger.error(f"Error retrieving memories: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@app.get("/v1/memory/all/{npc_id}")
async def get_all_npc_memories(
    npc_id: str,
    player_id: str = None,
    limit: int = 100
) -> Dict[str, Any]:
    """
    Get all memories for an NPC, optionally filtered by player.
    Useful for debugging or admin panels.
    """
    try:
        memories = memory_dao.get_all_for_npc(npc_id, player_id, limit)
        return {
            "npc_id": npc_id,
            "count": len(memories),
            "memories": [mem.model_dump() for mem in memories]
        }
    except Exception as e:
        logger.error(f"Error retrieving all memories: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


# ============================================================================
# HTTP: TEXT-TO-SPEECH
# ============================================================================

@app.post("/v1/voice/tts")
async def text_to_speech(request: TTSRequest) -> TTSResponse:
    """
    Synthesize SSML to audio using Google Cloud TTS.
    
    Request body:
    {
        "ssml": "<speak><prosody rate='95%'>Greetings, traveler.</prosody></speak>",
        "voice_name": "en-US-Neural2-C"
    }
    
    Returns:
    {
        "audio_url": "http://localhost:8000/media/abc123.mp3"
    }
    """
    try:
        audio_url = synthesize_ssml(request.ssml, request.voice_name)
        
        if not audio_url:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="TTS synthesis failed"
            )
        
        logger.info(f"TTS generated: {audio_url}")
        return TTSResponse(audio_url=audio_url)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"TTS error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


# ============================================================================
# UTILITY ENDPOINTS
# ============================================================================

@app.get("/healthz")
async def health_check() -> Dict[str, Any]:
    """
    Health check endpoint.
    Returns server status and configuration info.
    """
    return {
        "ok": True,
        "service": "rpgai",
        "version": "1.0.0",
        "model": settings.gemini_model,
        "memory_count": memory_dao.count_memories()
    }


@app.get("/")
async def root() -> Dict[str, str]:
    """Root endpoint with API info."""
    return {
        "service": "RPGAI - NPC Dialogue Service",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/healthz"
    }


# ============================================================================
# ERROR HANDLERS
# ============================================================================

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler for unhandled errors."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "Internal server error",
            "error": str(exc)
        }
    )


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=True,
        log_level=settings.log_level.lower()
    )

