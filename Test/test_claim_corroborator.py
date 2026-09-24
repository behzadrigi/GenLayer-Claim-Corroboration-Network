import json
import pytest
from genlayer_py import create_client, create_account
from genlayer_py.chains import localnet

CONTRACT_ADDRESS = "0xE11Db2071baBB4b80904c806aC1bf7114b7a51cb"
REGISTRY_ADDRESS = "0x57E6E64920eb8a7E2322D2bE5Cdd81C70f419154"


@pytest.fixture(scope="module")
def client():
    account = create_account()
    return create_client(chain=localnet, account=account)


def _write(client, address, function_name, args):
    tx_hash = client.write_contract(
        address=address, function_name=function_name, args=args, value=0,
    )
    return client.wait_for_transaction_receipt(transaction_hash=tx_hash, status="ACCEPTED")


def _read(client, address, function_name, args=None):
    return client.read_contract(
        address=address, function_name=function_name, args=args or [],
    )


def test_corroborate_verified_claim(client):
    _write(client, REGISTRY_ADDRESS, "submit_claim", [
        "Python is a programming language",
        "https://www.python.org,https://www.w3schools.com/python",
    ])
    claim_id = 1
    _write(client, CONTRACT_ADDRESS, "corroborate_claim", [claim_id])
    data = json.loads(_read(client, CONTRACT_ADDRESS, "get_corroboration_data", [claim_id]))
    assert data["status"] == "VERIFIED"
    assert data["verified_count"] == data["total_sources"]


def test_cannot_corroborate_twice(client):
    with pytest.raises(Exception, match="Already corroborated"):
        _write(client, CONTRACT_ADDRESS, "corroborate_claim", [1])


def test_corroborate_unrelated_claim(client):
    _write(client, REGISTRY_ADDRESS, "submit_claim", [
        "The Great Wall of China is visible from the Moon with the naked eye",
        "https://en.wikipedia.org/wiki/Great_Wall_of_China,https://www.nasa.gov",
    ])
    claim_id = 2
    _write(client, CONTRACT_ADDRESS, "corroborate_claim", [claim_id])
    data = json.loads(_read(client, CONTRACT_ADDRESS, "get_corroboration_data", [claim_id]))
    assert data["status"] in ("REJECTED", "PARTIAL")


def test_corroborate_nonexistent_claim(client):
    with pytest.raises(Exception, match="Claim not found in registry"):
        _write(client, CONTRACT_ADDRESS, "corroborate_claim", [999])


def test_list_corroborations(client):
    listing = _read(client, CONTRACT_ADDRESS, "list_corroborations")
    assert "1:VERIFIED" in listing
