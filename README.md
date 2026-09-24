# GenLayer Claim Corroboration Network

A 4-contract GenLayer Intelligent Contract suite that corroborates factual claims
across multiple independent, live sources, classifies them, and updates the
submitter's on-chain reputation — with every downstream action bound to the
authenticated on-chain output of the contract before it, never to caller-supplied
data.

## Why this exists

A claim is only as trustworthy as the evidence behind it. This suite requires at
least two independent sources (different URLs, different domains) per claim, has
every source fetched live on-chain, and only accepts a corroboration result once
independent GenLayer validators — each re-fetching and re-judging every source
from scratch — agree on it. Downstream contracts (classification, reputation)
never accept a JSON claim from a caller; they read the previous contract's
result directly from its own on-chain state.

This design applies every lesson learned across three earlier GenLayer
submissions on this account: identity bound to the real transaction sender, no
caller-supplied JSON trusted anywhere in the chain, independent full
recomputation of every consequential field (not just a status label), genuinely
independent sources, no early-claim races, and no double-application of a
result. See [DECISIONS.md](./DECISIONS.md) for the full rationale behind each of
these.

## Architecture

```
Caller
  │
  ▼
1. ClaimRegistry          deterministic — binds the claim to gl.message.sender_address,
                           normalizes and validates sources, enforces at least 2
                           sources with unique URLs and unique domains
  │
  ▼
2. ClaimCorroborator       non-deterministic, comparative consensus — fetches every
                           source live via gl.nondet.web.render, asks the model
                           whether each page corroborates the claim, and only
                           accepts a result once independent validators agree on
                           the status, the verified count, AND the exact set of
                           corroborating URLs
  │
  ▼
3. ClaimClassifier         non-deterministic, strict-equality consensus — a
                           deliberately different Equivalence Principle pattern:
                           a single fixed-vocabulary field (category) must match
                           exactly across independent validator runs
  │
  ▼
4. ReputationRegistry      deterministic — converts the corroboration result into
                           a 0-100 score and applies an INCREASE/DECREASE to the
                           claim's original submitter, but only once per claim
```

Each contract is deployed independently and reads its upstream contract's state
directly (`gl.get_contract_at(Address(...)).view().method(...)`); no contract
accepts a JSON blob describing another contract's result from a caller.

## Contracts and addresses (GenLayer Studio)

| Contract | Address |
|---|---|
| ClaimRegistry | `0x57E6E64920eb8a7E2322D2bE5Cdd81C70f419154` |
| ClaimCorroborator | `0xE11Db2071baBB4b80904c806aC1bf7114b7a51cb` |
| ClaimClassifier | `0x35d23982FE963261A232D88A16b095B4DC8baacC` |
| ReputationRegistry | `0x8F7230ec8F78348586f631bbA9F7Cd6bb0575728` |

See [CONTRACTS.md](./CONTRACTS.md) for per-contract detail and safety properties,
and [tests/](./tests) for integration tests against the addresses above.

## Repo structure

```
contracts/
  ClaimRegistry.py
  ClaimCorroborator.py
  ClaimClassifier.py
  ReputationRegistry.py
tests/
  test_claim_registry.py
  test_claim_corroborator.py
  test_claim_classifier.py
  test_reputation_registry.py
README.md
CONTRACTS.md
DECISIONS.md
LICENSE
```
