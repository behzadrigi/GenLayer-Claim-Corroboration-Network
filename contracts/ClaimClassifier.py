# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }

import json

from genlayer import *
from dataclasses import dataclass

ALLOWED_CATEGORIES = ("SCIENCE", "HISTORY", "CURRENT_EVENTS", "TECHNOLOGY", "OTHER")


def classify_one(claim: str) -> str:
    prompt = f"""
    Claim: {claim}

    Classify this claim into exactly one category.
    Allowed categories: SCIENCE, HISTORY, CURRENT_EVENTS, TECHNOLOGY, OTHER

    Respond with ONLY the category word, nothing else. Example: SCIENCE
    """
    response = gl.nondet.exec_prompt(prompt)
    category = str(response).strip().upper()
    for allowed in ALLOWED_CATEGORIES:
        if allowed in category:
            return allowed
    return "OTHER"


@allow_storage
@dataclass
class ClassificationRecord:
    claim_id: u256
    agent: str
    category: str
    status: str  # CLASSIFIED


class ClaimClassifier(gl.Contract):
    classifications: TreeMap[u256, ClassificationRecord]
    corroborator_contract: str

    def __init__(self, corroborator_address: str):
        self.corroborator_contract = corroborator_address

    @gl.public.write
    def classify_claim(self, claim_id: u256) -> bool:
        assert claim_id not in self.classifications, "Already classified"

        raw = gl.get_contract_at(
            Address(self.corroborator_contract)
        ).view().get_corroboration_data(claim_id)

        assert raw != "NOT_FOUND", "Corroboration not found"

        try:
            data = json.loads(raw)
        except:
            raise gl.vm.UserError("Invalid data from corroborator")

        status = data.get("status", "")
        assert status in ("VERIFIED", "PARTIAL"), "Claim was not sufficiently corroborated"

        agent = data.get("agent", "")
        claim = data.get("claim", "")
        assert agent != "", "Agent not found in corroboration record"

        # Equivalence Principle: STRICT EQUALITY on a single structured field.
        # Deliberately different pattern from ClaimCorroborator's multi-field
        # comparative check — a single fixed-vocabulary field is far more
        # likely to match exactly across independent leader/validator runs
        # than free-form or multi-field output would be.
        def leader_fn():
            return {"category": classify_one(claim)}

        def validator_fn(leader_result):
            if not isinstance(leader_result, gl.vm.Return):
                return False
            leader_category = leader_result.calldata.get("category")
            if leader_category not in ALLOWED_CATEGORIES:
                return False
            my_category = classify_one(claim)
            return my_category == leader_category

        result = gl.vm.run_nondet_unsafe(leader_fn, validator_fn)

        self.classifications[claim_id] = ClassificationRecord(
            claim_id=claim_id,
            agent=agent,
            category=result["category"],
            status="CLASSIFIED",
        )

        return True

    @gl.public.view
    def get_classification(self, claim_id: u256) -> str:
        if claim_id not in self.classifications:
            return "NOT_FOUND"
        c = self.classifications[claim_id]
        return f"{c.category}:{c.status}"

    @gl.public.view
    def get_classification_data(self, claim_id: u256) -> str:
        if claim_id not in self.classifications:
            return "NOT_FOUND"
        c = self.classifications[claim_id]
        return json.dumps({
            "claim_id": int(c.claim_id),
            "agent": c.agent,
            "category": c.category,
            "status": c.status,
        })

    @gl.public.view
    def list_classifications(self) -> str:
        items = []
        for key in self.classifications:
            c = self.classifications[key]
            items.append(f"{int(c.claim_id)}:{c.category}")
        return ",".join(items)
