# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }

import json

from genlayer import *
from dataclasses import dataclass


@allow_storage
@dataclass
class ReputationChange:
    change_id: u256
    agent: str
    claim_id: u256
    final_score: u256
    change_type: str  # INCREASE, DECREASE, NEUTRAL
    status: str  # APPLIED


class ReputationRegistry(gl.Contract):
    changes: TreeMap[u256, ReputationChange]
    applied_claims: TreeMap[u256, bool]
    next_id: u256
    reputation: TreeMap[str, u256]
    corroborator_contract: str

    def __init__(self, corroborator_address: str):
        self.next_id = u256(0)
        self.corroborator_contract = corroborator_address
        # No initialize_reputation method: self.reputation.get(agent, u256(50))
        # below provides a lazy default of 50 on first encounter, which removes
        # the race where a caller could claim/init an agent's reputation first.

    @gl.public.write
    def apply_reputation(self, claim_id: u256) -> u256:
        assert claim_id not in self.applied_claims, "Claim already applied"

        raw = gl.get_contract_at(
            Address(self.corroborator_contract)
        ).view().get_corroboration_data(claim_id)

        assert raw != "NOT_FOUND", "Corroboration not found"

        try:
            data = json.loads(raw)
        except:
            raise gl.vm.UserError("Invalid data from corroborator")

        status = data.get("status", "")
        assert status in ("VERIFIED", "PARTIAL", "REJECTED"), "Claim not yet corroborated"

        agent = data.get("agent", "")
        assert agent != "", "Agent not found in corroboration record"

        verified_count = data.get("verified_count", 0)
        total_sources = data.get("total_sources", 1)

        base_score = (verified_count / total_sources) * 100
        if status == "VERIFIED":
            multiplier = 1.0
        elif status == "PARTIAL":
            multiplier = 0.7
        else:
            multiplier = 0.3

        final_score = int(base_score * multiplier)
        final_score = min(100, max(0, final_score))
        score_status = "APPROVED" if final_score >= 50 else "REJECTED"

        assert score_status == "APPROVED", "Score not approved"

        current_reputation = self.reputation.get(agent, u256(50))
        new_score = u256(final_score)

        if new_score > current_reputation + u256(10):
            change_type = "INCREASE"
        elif new_score < current_reputation - u256(10):
            change_type = "DECREASE"
        else:
            change_type = "NEUTRAL"

        if change_type == "NEUTRAL":
            raise gl.vm.UserError("Change too small to apply")

        self.reputation[agent] = new_score
        self.applied_claims[claim_id] = True

        cid = self.next_id
        self.next_id += u256(1)

        self.changes[cid] = ReputationChange(
            change_id=cid,
            agent=agent,
            claim_id=claim_id,
            final_score=u256(final_score),
            change_type=change_type,
            status="APPLIED",
        )

        return cid

    @gl.public.view
    def get_reputation(self, agent: str) -> str:
        score = self.reputation.get(agent, u256(50))
        return f"REPUTATION:{int(score)}"

    @gl.public.view
    def is_claim_applied(self, claim_id: u256) -> str:
        return "APPLIED" if claim_id in self.applied_claims else "NOT_APPLIED"

    @gl.public.view
    def get_change_details(self, change_id: u256) -> str:
        if change_id not in self.changes:
            return "NOT_FOUND"
        c = self.changes[change_id]
        return json.dumps({
            "change_id": int(c.change_id),
            "agent": c.agent,
            "claim_id": int(c.claim_id),
            "final_score": int(c.final_score),
            "change_type": c.change_type,
            "status": c.status,
        })

    @gl.public.view
    def list_changes(self) -> str:
        items = []
        for key in self.changes:
            c = self.changes[key]
            items.append(f"{int(c.change_id)}:{c.change_type}")
        return ",".join(items)

    @gl.public.view
    def get_agent_changes(self, agent: str) -> str:
        items = []
        for key in self.changes:
            c = self.changes[key]
            if c.agent == agent:
                items.append(str(int(c.change_id)))
        return ",".join(items)
