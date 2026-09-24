import json
import pytest
from genlayer_py import create_client, create_account
from genlayer_py.chains import localnet

CONTRACT_ADDRESS = "0x8F7230ec8F78348586f631bbA9F7Cd6bb0575728"


@pytest.fixture(scope="module")
def client():
    account = create_account()
    return create_client(chain=localnet, account=account)


def _write(client, function_name, args):
    tx_hash = client.write_contract(
        address=CONTRACT_ADDRESS, function_name=function_name, args=args, value=0,
    )
    return client.wait_for_transaction_receipt(transaction_hash=tx_hash, status="ACCEPTED")


def _read(client, function_name, args=None):
    return client.read_contract(
        address=CONTRACT_ADDRESS, function_name=function_name, args=args or [],
    )


def test_lazy_default_reputation(client, sender_address):
    """No initialize_reputation exists; first read should be the lazy default of 50."""
    assert _read(client, "get_reputation", [sender_address]) == "REPUTATION:50"


def test_apply_reputation_for_verified_claim(client, sender_address):
    """Assumes claim_id=1 (VERIFIED) from test_claim_corroborator.py already ran."""
    _write(client, "apply_reputation", [1])
    change = json.loads(_read(client, "get_change_details", [0]))
    assert change["agent"] == sender_address
    assert change["change_type"] == "INCREASE"
    assert _read(client, "get_reputation", [sender_address]) == "REPUTATION:100"


def test_cannot_apply_same_claim_twice(client):
    with pytest.raises(Exception, match="Claim already applied"):
        _write(client, "apply_reputation", [1])


def test_rejected_claim_cannot_be_applied(client):
    """Assumes claim_id=2 (REJECTED) from test_claim_corroborator.py already ran."""
    with pytest.raises(Exception, match="Score not approved"):
        _write(client, "apply_reputation", [2])
