# Contracts

## 1. ClaimRegistry

**Pattern:** fully deterministic — no LLM, no consensus needed.

**Purpose:** the entry gate for every claim. Binds the claim to the real
transaction sender, normalizes every source URL, and enforces that sources are
genuinely independent.

**Public methods**
- `submit_claim(claim: str, sources: str) -> u256` — stores a claim; returns its
  `claim_id`.
- `get_claim_status(claim_id) -> str`
- `get_claim_details(claim_id) -> str` (JSON)
- `get_claim_data(claim_id) -> str` (JSON, for downstream reads)
- `list_claims() -> str`
- `get_agent_claims(agent) -> str`

**Safety properties**
- `agent` is always `gl.message.sender_address`; it is never accepted as a
  caller-supplied parameter, so nobody can submit a claim under another
  agent's identity.
- At least 2 sources are required; a source list with a duplicate URL or two
  URLs from the same domain always reverts (`submit_claim` cannot be tricked
  into treating one source, or one domain, as "multiple independent
  sources").
- An unparseable URL always reverts before any state is written.

---

## 2. ClaimCorroborator

**Pattern:** non-deterministic, Equivalence-Principle consensus
(`gl.vm.run_nondet_unsafe` with a `leader_fn`/`validator_fn` pair), web-grounded,
comparative (multiple fields checked).

**Purpose:** fetches every source URL for a claim live and asks the model
whether each page's content corroborates the claim. The result is only written
to state once independent validators, each re-running the same fetch-and-judge
routine from scratch, agree on every field.

**Public methods**
- `corroborate_claim(claim_id) -> bool` — reads the claim from `ClaimRegistry`
  on-chain and runs the consensus check; can only be called once per claim.
- `get_corroboration_status(claim_id) -> str`
- `get_corroboration_data(claim_id) -> str` (JSON, includes `agent`, for
  downstream reads)
- `list_corroborations() -> str`

**Safety properties**
- The claim text, sources, and agent are read directly from `ClaimRegistry`'s
  own on-chain state — never supplied by the caller of `corroborate_claim`.
- `corroborate_claim` cannot be called twice on the same claim (`assert
  claim_id not in self.records` is checked before any consensus work runs, and
  the record is only written after consensus succeeds — a failed or reverted
  attempt never "consumes" the claim).
- Every validator independently re-fetches every source and re-runs the
  judgment; a validator that computes a different `status`, `verified_count`,
  or `verified_urls` set than the leader rejects the leader's result. Nothing
  is accepted on the strength of the leader's label alone.
- `status` is always one of `VERIFIED` (all sources corroborate), `PARTIAL`
  (≥50% corroborate), or `REJECTED` (<50%), and the invariant between
  `verified_count`/`total` and `status` is checked independently by every
  validator, not just range-checked by the leader.

---

## 3. ClaimClassifier

**Pattern:** non-deterministic, Equivalence-Principle consensus, **strict
equality** on a single fixed-vocabulary field — deliberately different from
ClaimCorroborator's multi-field comparative pattern.

**Purpose:** classifies an already-corroborated claim into one of five fixed
categories (`SCIENCE`, `HISTORY`, `CURRENT_EVENTS`, `TECHNOLOGY`, `OTHER`).

**Public methods**
- `classify_claim(claim_id) -> bool` — reads the corroboration result from
  `ClaimCorroborator` on-chain; only allowed for `VERIFIED` or `PARTIAL`
  claims.
- `get_classification(claim_id) -> str`
- `get_classification_data(claim_id) -> str` (JSON)
- `list_classifications() -> str`

**Safety properties**
- `classify_claim` reverts on a `REJECTED` (or missing) corroboration result —
  a claim that was never sufficiently corroborated can never be classified.
- The `category` field must match exactly across independent leader/validator
  runs; a single fixed-vocabulary word is far more likely to be reproducible
  than a free-form or multi-field output, which is why this contract
  deliberately uses a different, simpler Equivalence Principle shape than
  ClaimCorroborator.
- `classify_claim` cannot be called twice on the same claim.
- `agent` is read from `ClaimCorroborator`'s authenticated record, never
  supplied by the caller.

---

## 4. ReputationRegistry

**Pattern:** fully deterministic — deliberately no LLM/consensus, since
converting an already-corroborated result into a score and a reputation change
is bookkeeping, not judgment.

**Purpose:** applies an `INCREASE`/`DECREASE` to the claim's original
submitter's on-chain reputation, based on the `ClaimCorroborator` result.

**Public methods**
- `apply_reputation(claim_id) -> u256` — reads the corroboration result
  on-chain, computes a 0-100 score, and applies a reputation change if
  `APPROVED` (score ≥ 50).
- `get_reputation(agent) -> str`
- `is_claim_applied(claim_id) -> str`
- `get_change_details(change_id) -> str` (JSON)
- `list_changes() -> str`
- `get_agent_changes(agent) -> str`

**Safety properties**
- `agent` is read from `ClaimCorroborator`'s on-chain record, not supplied by
  the caller of `apply_reputation` — nobody can pair a legitimately-approved
  `claim_id` with an unrelated agent's address.
- `apply_reputation` reverts outright ("Score not approved") unless the
  computed score is ≥ 50 — a `REJECTED` or low-`PARTIAL` corroboration can
  never move reputation.
- `apply_reputation` cannot be called twice on the same `claim_id`
  ("Claim already applied").
- There is no `initialize_reputation` method: `self.reputation.get(agent,
  u256(50))` provides a lazy default of 50 the first time an agent is read or
  changed, which removes any race to "claim" an agent's starting reputation
  before its owner does.
- A change smaller than 10 points is classified `NEUTRAL` and reverts rather
  than being silently applied.
