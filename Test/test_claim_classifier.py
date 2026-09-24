import json
import pytest
from genlayer_py import create_client, create_account
from genlayer_py.chains import localnet

CONTRACT_ADDRESS = "0x35d23982FE963261A232D88A16b095B4DC8baacC"

ALLOWED_CATEGORIES = ("SCIENCE", "HISTORY", "CURRENT_EVENTS", "TECHNOLOGY", "OTHER")


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


def test_classify_verified_claim(client):
    """Assumes claim_id=1 (VERIFIED) from test_claim_corroborator.py already ran."""
    _write(client, "classify_claim", [1])
    data = json.loads(_read(client, "get_classification_data", [1]))
    assert data["category"] in ALLOWED_CATEGORIES
    assert data["status"] == "CLASSIFIED"


def test_cannot_classify_twice(client):
    with pytest.raises(Exception, match="Already classified"):
        _write(client, "classify_claim", [1])


def test_cannot_classify_rejected_claim(client):
    """Assumes claim_id=2 (REJECTED) from test_claim_corroborator.py already ran."""
    with pytest.raises(Exception, match="Claim was not sufficiently corroborated"):
        _write(client, "classify_claim", [2])


def test_list_classifications(client):
    listing = _read(client, "list_classifications")
    assert "1:" in listing
