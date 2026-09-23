# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }

import json

from genlayer import *
from dataclasses import dataclass


def evaluate_one_source(url: str, claim: str) -> bool:
    try:
        content = gl.nondet.web.render(url)
    except:
        return False

    prompt = f"""
    Claim: {claim}

    Content from source ({url}):
    {content[:2000]}

    Does this content CORROBORATE the claim?
    Respond with ONLY: YES or NO
    """
    response = gl.nondet.exec_prompt(prompt)
    return "YES" in response.upper()


def compute_status(verified_count: int, total: int) -> str:
    if verified_count == total:
        return "VERIFIED"
    elif verified_count >= total // 2:
        return "PARTIAL"
    else:
        return "REJECTED"


@allow_storage
@dataclass
class CorroborationRecord:
    claim_id: u256
    agent: str
    claim: str
    verified_count: u256
    total_sources: u256
    status: str  # VERIFIED, PARTIAL, REJECTED
    verified_urls: str


class ClaimCorroborator(gl.Contract):
    records: TreeMap[u256, CorroborationRecord]
    registry_contract: str

    def __init__(self, registry_address: str):
        self.registry_contract = registry_address

    @gl.public.write
    def corroborate_claim(self, claim_id: u256) -> bool:
        assert claim_id not in self.records, "Already corroborated"

        raw = gl.get_contract_at(
            Address(self.registry_contract)
        ).view().get_claim_data(claim_id)

        assert raw != "NOT_FOUND", "Claim not found in registry"

        try:
            data = json.loads(raw)
        except:
            raise gl.vm.UserError("Invalid data from registry")

        agent = data.get("agent", "")
        claim = data.get("claim", "")
        sources = data.get("sources", "")
        assert agent != "", "Agent not found in claim record"

        source_list = [s.strip() for s in sources.split(',') if s.strip()]
        assert len(source_list) >= 2, "At least 2 sources required"

        def leader_fn():
            corroborated_urls = []
            for src in source_list:
                if evaluate_one_source(src, claim):
                    corroborated_urls.append(src)
            verified_count = len(corroborated_urls)
            total = len(source_list)
            status = compute_status(verified_count, total)
            return {
                "verified_count": verified_count,
                "total": total,
                "status": status,
                "verified_urls": ",".join(sorted(corroborated_urls)),
            }

        def validator_fn(leader_result):
            if not isinstance(leader_result, gl.vm.Return):
                return False

            leader_data = leader_result.calldata
            leader_count = leader_data.get("verified_count")
            leader_total = leader_data.get("total")
            leader_status = leader_data.get("status")
            leader_urls_str = leader_data.get("verified_urls", "")

            if not isinstance(leader_count, int) or not isinstance(leader_total, int):
                return False
            if leader_total != len(source_list):
                return False
            if leader_status not in ("VERIFIED", "PARTIAL", "REJECTED"):
                return False
            if leader_count < 0 or leader_count > leader_total:
                return False

            validator_urls = [src for src in source_list if evaluate_one_source(src, claim)]
            validator_count = len(validator_urls)
            validator_status = compute_status(validator_count, len(source_list))

            expected_status = compute_status(leader_count, leader_total)
            if expected_status != leader_status:
                return False
            if validator_count != leader_count:
                return False
            if validator_status != leader_status:
                return False

            leader_set = set(u for u in leader_urls_str.split(',') if u)
            validator_set = set(validator_urls)
            if leader_set != validator_set:
                return False

            return True

        result = gl.vm.run_nondet_unsafe(leader_fn, validator_fn)

        self.records[claim_id] = CorroborationRecord(
            claim_id=claim_id,
            agent=agent,
            claim=claim,
            verified_count=u256(result["verified_count"]),
            total_sources=u256(result["total"]),
            status=result["status"],
            verified_urls=result["verified_urls"],
        )

        return True

    @gl.public.view
    def get_corroboration_status(self, claim_id: u256) -> str:
        if claim_id not in self.records:
            return "NOT_FOUND"
        r = self.records[claim_id]
        return f"{r.status}:{int(r.verified_count)}/{int(r.total_sources)}"

    @gl.public.view
    def get_corroboration_data(self, claim_id: u256) -> str:
        if claim_id not in self.records:
            return "NOT_FOUND"
        r = self.records[claim_id]
        return json.dumps({
            "claim_id": int(r.claim_id),
            "agent": r.agent,
            "claim": r.claim,
            "verified_count": int(r.verified_count),
            "total_sources": int(r.total_sources),
            "status": r.status,
            "verified_urls": r.verified_urls,
        })

    @gl.public.view
    def list_corroborations(self) -> str:
        items = []
        for key in self.records:
            r = self.records[key]
            items.append(f"{int(r.claim_id)}:{r.status}")
        return ",".join(items)
