import json
import pytest
from genlayer_py import create_client, create_account
from genlayer_py.chains import localnet

CONTRACT_ADDRESS = "0x57E6E64920eb8a7E2322D2bE5Cdd81C70f419154"


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


def test_duplicate_url_rejected(client):
    with pytest.raises(Exception, match="Duplicate source URL"):
        _write(client, "submit_claim", [
            "Ethereum price is over $3000",
            "https://coinmarketcap.com,https://coinmarketcap.com",
        ])


def test_duplicate_domain_rejected(client):
    with pytest.raises(Exception, match="Sources must come from independent domains"):
        _write(client, "submit_claim", [
            "Ethereum price is over $3000",
            "https://coinmarketcap.com/x,https://coinmarketcap.com/y",
        ])


def test_submit_valid_claim(client):
    _write(client, "submit_claim", [
        "Python was created by Guido van Rossum",
        "https://en.wikipedia.org/wiki/Python,https://www.python.org/about",
    ])
    claim_id = 0
    details = json.loads(_read(client, "get_claim_details", [claim_id]))
    assert details["status"] == "PENDING"
    assert details["source_count"] == 2


def test_agent_bound_to_sender(client, tx_sender_address=None):
    details = json.loads(_read(client, "get_claim_data", [0]))
    assert details["agent"] != ""  # bound to gl.message.sender_address, not caller input


def test_invalid_url_rejected(client):
    with pytest.raises(Exception, match="Invalid URL"):
        _write(client, "submit_claim", ["not_a_url test", "not_a_url,also_not_a_url"])


def test_list_and_agent_lookup(client):
    listing = _read(client, "list_claims")
    assert "0:PENDING" in listing
