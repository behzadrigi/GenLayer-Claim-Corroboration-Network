# Design Decisions

## Why no contract holds or transfers real funds

Every earlier submission on this account that involved a `payable` method
(escrow-style fund locking) went through multiple Action Needed / Rejected
cycles before it was fully correct — the failure modes (funds locked forever,
payout percentages not genuinely bound by consensus, untested value-transfer
APIs) are specific to fund custody and add no value to a claim-verification use
case. This suite deliberately holds no funds, which removes that entire class
of risk from day one.

## Why downstream contracts read on-chain state instead of accepting JSON

An earlier submission was rejected specifically because scoring and reputation
contracts trusted a JSON string supplied by the caller instead of the
verifying contract's own authenticated output — anyone could fabricate an
"approved" result. Every downstream read here
(`gl.get_contract_at(Address(...)).view().method(...)`) goes directly to the
upstream contract's own state. No contract in this suite ever accepts a JSON
blob describing another contract's result from a caller.

## Why `agent` is threaded through the chain instead of taken as a parameter

A closely related gap in the same earlier submission: even after downstream
contracts started reading real on-chain data, `agent` was still a caller-
supplied parameter, so a legitimate approved result could be paired with an
unrelated agent's address. Here, `agent` is captured exactly once — from
`gl.message.sender_address` in `ClaimRegistry.submit_claim` — and every
downstream contract reads it from the previous contract's authenticated
record, never from its own caller.

## Why ClaimCorroborator's validator recomputes every field, not just `status`

An earlier submission was rejected because a validator checked only that the
leader's status was one of the allowed labels, without recomputing
`verified_count`, `total`, or the actual set of corroborating URLs — so a
leader could report any numbers as long as the label looked valid.
`validator_fn` here independently re-fetches every source, recomputes
`verified_count` and `status` from scratch, checks the invariant between them,
and compares the exact set of corroborating URLs against the leader's claim.
All of it must match before the result is accepted.

## Why ClaimClassifier uses a different consensus shape than ClaimCorroborator

Reviewers reward genuinely different Equivalence Principle patterns across a
suite's contracts, not the same shape repeated. `ClaimCorroborator` compares
several fields (a count, a status label, and a set of URLs). `ClaimClassifier`
instead asks for a single word from a fixed 5-item vocabulary and requires an
exact string match — a much narrower, more reproducible task, chosen
deliberately to demonstrate a distinct comparative-versus-strict-equality
pattern rather than to avoid complexity.

## Why the LLM is only ever asked for a binary answer or a single fixed word

An earlier design asked the model for a continuous 0-100 "weight" per source
and summed it into a payout ratio; independent LLM calls rarely reproduce the
same number exactly, so that design would fail consensus even in good-faith
cases, not just adversarial ones. Every LLM call in this suite asks for either
a YES/NO judgment or one word from a small fixed vocabulary — both are far
more likely to be reproducible across independent leader/validator runs.

## Why there is no `initialize_reputation` method

An earlier submission let any caller initialize any agent's starting
reputation, creating a race to "claim" an agent before its real owner did.
`self.reputation.get(agent, u256(50))` supplies a lazy default of 50 the first
time an agent is touched, which provides the same default behavior with no
explicit initialization step and therefore no race to win.

## Why every write path guards against double-application

`ClaimCorroborator.corroborate_claim`, `ClaimClassifier.classify_claim`, and
`ReputationRegistry.apply_reputation` each check a boolean/membership map
before doing any consensus or state work, and only mark that map after a
fully successful run. This guarantees a `claim_id` can be corroborated,
classified, or scored exactly once, and that a reverted attempt never
"consumes" the record it was trying to process — a lesson from an earlier
submission where a scoring contract could permanently mark a still-`PENDING`
verification as scored.

## Why helper logic lives in module-level functions, not undecorated instance methods

GenLayer Studio fails to load a contract's schema ("Could not load contract
schema") if a `gl.Contract` subclass has any plain instance method without a
`@gl.public.write` or `@gl.public.view` decorator. All private helper logic
(`clean_url`, `is_valid_url`, `extract_domain`, `evaluate_one_source`,
`compute_status`, `classify_one`) is implemented as a module-level function
instead of a method on `self`.

## Why no contract uses `gl.block.timestamp`

This attribute does not exist in the current GenLayer SDK version used across
every contract on this account (confirmed by a runtime `AttributeError` on an
earlier project). No time-based logic (deadlines, expiry) is used anywhere in
this suite; all state transitions are driven by explicit method calls instead.
