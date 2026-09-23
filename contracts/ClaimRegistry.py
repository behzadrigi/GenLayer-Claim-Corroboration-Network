# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }

import json
import re

from genlayer import *
from dataclasses import dataclass


def clean_url(url: str):
    if not url:
        return None
    cleaned = url.strip().rstrip('/')
    if cleaned.startswith('http://'):
        cleaned = cleaned.replace('http://', 'https://', 1)
    cleaned = cleaned.replace(' ', '')
    if '?' in cleaned:
        cleaned = cleaned.split('?')[0]
    return cleaned if cleaned else None


def is_valid_url(url: str) -> bool:
    pattern = re.compile(
        r'^(https?://)'
        r'([a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}'
        r'(/[\w\-./?%&=]*)?$'
    )
    return bool(pattern.match(url.strip()))


def extract_domain(url: str):
    try:
        without_protocol = re.sub(r'^https?://', '', url)
        domain = without_protocol.split('/')[0]
        return re.sub(r'^www\.', '', domain)
    except Exception:
        return None


@allow_storage
@dataclass
class ClaimRecord:
    claim_id: u256
    agent: str
    claim: str
    sources: str
    source_count: u256
    status: str  # PENDING (corroboration happens in ClaimCorroborator)


class ClaimRegistry(gl.Contract):
    claims: TreeMap[u256, ClaimRecord]
    next_id: u256

    def __init__(self):
        self.next_id = u256(0)

    @gl.public.write
    def submit_claim(self, claim: str, sources: str) -> u256:
        agent = str(gl.message.sender_address)

        assert claim.strip() != "", "Claim cannot be empty"
        assert sources.strip() != "", "Sources cannot be empty"

        raw_list = sources.split(',')
        assert len(raw_list) >= 2, "At least 2 sources required"

        normalized_list = []
        domain_list = []
        for src in raw_list:
            cleaned = clean_url(src)
            assert cleaned is not None, f"Invalid URL: {src}"
            assert is_valid_url(cleaned), f"Invalid URL: {cleaned}"
            domain = extract_domain(cleaned)
            assert domain is not None, f"Could not extract domain from: {cleaned}"
            normalized_list.append(cleaned)
            domain_list.append(domain)

        assert len(set(normalized_list)) == len(normalized_list), "Duplicate source URL"
        assert len(set(domain_list)) == len(domain_list), "Sources must come from independent domains"

        cid = self.next_id
        self.next_id += u256(1)

        self.claims[cid] = ClaimRecord(
            claim_id=cid,
            agent=agent,
            claim=claim,
            sources=",".join(normalized_list),
            source_count=u256(len(normalized_list)),
            status="PENDING",
        )

        return cid

    @gl.public.view
    def get_claim_status(self, claim_id: u256) -> str:
        if claim_id not in self.claims:
            return "NOT_FOUND"
        return self.claims[claim_id].status

    @gl.public.view
    def get_claim_details(self, claim_id: u256) -> str:
        if claim_id not in self.claims:
            return "NOT_FOUND"
        c = self.claims[claim_id]
        return json.dumps({
            "claim_id": int(c.claim_id),
            "agent": c.agent,
            "claim": c.claim,
            "sources": c.sources,
            "source_count": int(c.source_count),
            "status": c.status,
        })

    @gl.public.view
    def get_claim_data(self, claim_id: u256) -> str:
        if claim_id not in self.claims:
            return "NOT_FOUND"
        c = self.claims[claim_id]
        return json.dumps({
            "claim_id": int(c.claim_id),
            "agent": c.agent,
            "claim": c.claim,
            "sources": c.sources,
            "source_count": int(c.source_count),
        })

    @gl.public.view
    def list_claims(self) -> str:
        items = []
        for key in self.claims:
            c = self.claims[key]
            items.append(f"{int(c.claim_id)}:{c.status}")
        return ",".join(items)

    @gl.public.view
    def get_agent_claims(self, agent: str) -> str:
        items = []
        for key in self.claims:
            c = self.claims[key]
            if c.agent == agent:
                items.append(str(int(c.claim_id)))
        return ",".join(items)
