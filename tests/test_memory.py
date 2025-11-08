"""
Unit tests for the memory system (SQLite DAO).
Tests read/write operations and salience×recency retrieval.
"""
import pytest
import tempfile
import os
from pathlib import Path

from server.memory import MemoryDAO
from server.schemas import NpcMemoryWrite


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    yield path
    # Cleanup
    if os.path.exists(path):
        os.remove(path)


@pytest.fixture
def dao(temp_db):
    """Create a MemoryDAO instance with temp database."""
    return MemoryDAO(temp_db)


def test_init_creates_tables(temp_db):
    """Test that initialization creates the required tables."""
    dao = MemoryDAO(temp_db)
    assert os.path.exists(temp_db)
    
    # Verify table exists by trying to query it
    count = dao.count_memories()
    assert count == 0


def test_write_and_retrieve_single_memory(dao):
    """Test writing a single memory and retrieving it."""
    row_id = dao.write(
        npc_id="elenor",
        player_id="p1",
        text="Player returned lost ring",
        salience=2,
        private=True,
        keys=["ring", "kindness"]
    )
    
    assert row_id > 0
    
    # Retrieve memories
    memories = dao.top("elenor", "p1", k=5)
    assert len(memories) == 1
    
    mem = memories[0]
    assert mem.npc_id == "elenor"
    assert mem.player_id == "p1"
    assert mem.text == "Player returned lost ring"
    assert mem.salience == 2
    assert mem.private is True


def test_salience_ordering(dao):
    """Test that memories are retrieved by salience (higher first)."""
    # Write memories with different salience levels
    dao.write("elenor", "p1", "Low importance", salience=0)
    dao.write("elenor", "p1", "Medium importance", salience=1)
    dao.write("elenor", "p1", "Critical event", salience=3)
    dao.write("elenor", "p1", "High importance", salience=2)
    
    # Retrieve top 3
    memories = dao.top("elenor", "p1", k=3)
    
    assert len(memories) == 3
    # Should be ordered by salience DESC
    assert memories[0].salience == 3
    assert memories[1].salience == 2
    assert memories[2].salience == 1


def test_recency_ordering(dao):
    """Test that memories of equal salience are ordered by recency."""
    import time
    
    # Write multiple memories with same salience
    dao.write("elenor", "p1", "First event", salience=1, ts=1000)
    time.sleep(0.01)  # Ensure different timestamps
    dao.write("elenor", "p1", "Second event", salience=1, ts=2000)
    time.sleep(0.01)
    dao.write("elenor", "p1", "Third event", salience=1, ts=3000)
    
    # Retrieve all
    memories = dao.top("elenor", "p1", k=10)
    
    # Should be ordered by recency (most recent first) for same salience
    assert memories[0].text == "Third event"
    assert memories[1].text == "Second event"
    assert memories[2].text == "First event"


def test_isolation_between_npcs(dao):
    """Test that memories are isolated per NPC."""
    dao.write("elenor", "p1", "Event with Elenor", salience=2)
    dao.write("garrick", "p1", "Event with Garrick", salience=2)
    
    # Retrieve for each NPC
    elenor_mems = dao.top("elenor", "p1", k=5)
    garrick_mems = dao.top("garrick", "p1", k=5)
    
    assert len(elenor_mems) == 1
    assert len(garrick_mems) == 1
    assert elenor_mems[0].text == "Event with Elenor"
    assert garrick_mems[0].text == "Event with Garrick"


def test_isolation_between_players(dao):
    """Test that memories are isolated per player."""
    dao.write("elenor", "p1", "Event with Player 1", salience=2)
    dao.write("elenor", "p2", "Event with Player 2", salience=2)
    
    # Retrieve for each player
    p1_mems = dao.top("elenor", "p1", k=5)
    p2_mems = dao.top("elenor", "p2", k=5)
    
    assert len(p1_mems) == 1
    assert len(p2_mems) == 1
    assert p1_mems[0].text == "Event with Player 1"
    assert p2_mems[0].text == "Event with Player 2"


def test_min_salience_filter(dao):
    """Test filtering by minimum salience."""
    dao.write("elenor", "p1", "Trivial event", salience=0)
    dao.write("elenor", "p1", "Minor event", salience=1)
    dao.write("elenor", "p1", "Important event", salience=2)
    
    # Retrieve with min_salience=2
    memories = dao.top("elenor", "p1", k=10, min_salience=2)
    
    assert len(memories) == 1
    assert memories[0].text == "Important event"


def test_write_from_model(dao):
    """Test writing from a Pydantic model."""
    memory = NpcMemoryWrite(
        npc_id="elenor",
        player_id="p1",
        text="Model-based write",
        salience=2,
        keys=["test"],
        private=True
    )
    
    row_id = dao.write_from_model(memory)
    assert row_id > 0
    
    memories = dao.top("elenor", "p1", k=5)
    assert len(memories) == 1
    assert memories[0].text == "Model-based write"


def test_text_truncation(dao):
    """Test that long text is truncated to 160 chars."""
    long_text = "A" * 200
    
    dao.write("elenor", "p1", long_text, salience=1)
    
    memories = dao.top("elenor", "p1", k=1)
    assert len(memories[0].text) == 160


def test_salience_validation(dao):
    """Test that invalid salience raises error."""
    with pytest.raises(ValueError):
        dao.write("elenor", "p1", "Invalid salience", salience=5)
    
    with pytest.raises(ValueError):
        dao.write("elenor", "p1", "Negative salience", salience=-1)


def test_count_memories(dao):
    """Test counting memories."""
    assert dao.count_memories() == 0
    
    dao.write("elenor", "p1", "Event 1", salience=1)
    dao.write("elenor", "p1", "Event 2", salience=1)
    dao.write("garrick", "p1", "Event 3", salience=1)
    
    assert dao.count_memories() == 3
    assert dao.count_memories(npc_id="elenor") == 2
    assert dao.count_memories(npc_id="garrick") == 1


def test_get_all_for_npc(dao):
    """Test retrieving all memories for an NPC."""
    dao.write("elenor", "p1", "Event 1", salience=1)
    dao.write("elenor", "p1", "Event 2", salience=2)
    dao.write("elenor", "p2", "Event 3", salience=1)
    
    # Get all for NPC (all players)
    all_mems = dao.get_all_for_npc("elenor")
    assert len(all_mems) == 3
    
    # Get all for NPC + specific player
    p1_mems = dao.get_all_for_npc("elenor", player_id="p1")
    assert len(p1_mems) == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

