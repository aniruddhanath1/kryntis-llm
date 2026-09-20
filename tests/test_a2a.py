"""Tests for kryntis.a2a subsystem."""

import pytest
from kryntis.a2a import AgentCard, A2AHandshake

def test_agent_card_schema():
    card = AgentCard(name="Kryntis Peer", url="http://localhost:8000/a2a", version="4.0.0")
    data = card.to_dict()
    assert data["name"] == "Kryntis Peer"
    assert data["version"] == "4.0.0"
    assert data["capabilities"]["streaming"] is True

def test_a2a_handshake_verification():
    handshake = A2AHandshake(secret_key="unit-test-secret")
    challenge = handshake.generate_challenge(agent_id="agent-007")
    assert handshake.verify_challenge(challenge) is True
    assert handshake.verify_challenge("corrupted:challenge:string") is False
