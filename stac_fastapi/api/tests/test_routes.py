"""Tests for extract_headers' JWT signature verification and _authorize_workspace.

The bug being fixed here: jwt.decode was called with options={"verify_signature": False},
so any claim in a Bearer token - including "workspaces" - was trusted without the token
ever having to be genuinely signed by Keycloak. That claim also fed X-Workspaces, which is
used for read filtering everywhere downstream, so a bug here lets every workspace-access
check elsewhere in the app be bypassed with whatever claims an attacker likes.

Separately, transaction endpoints (create/update/delete item, collection, catalog) take a
client-supplied `workspace` field alongside the verified token. _authorize_workspace is
the check that a write actually targets a workspace the caller's token grants.

There is no private key for the real Keycloak instance, so these sign with a throwaway
RSA keypair and mock stac_fastapi.api.routes._jwks_client() to hand back its public half,
rather than calling the real endpoint over the network.
"""

import types
from collections.abc import Iterator
from unittest.mock import patch

import jwt
import jwt.utils
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPrivateKey
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from stac_fastapi.api import routes

PRIVATE_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)


def _token(key: RSAPrivateKey, aud: str = "account", **claims: object) -> str:
    claims = {"sub": "test-user", "preferred_username": "test-user", "aud": aud, **claims}
    return jwt.encode(claims, key, algorithm="RS256")


def _credentials(token: str) -> HTTPAuthorizationCredentials:
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)


@pytest.fixture(autouse=True)
def mock_jwks() -> Iterator[None]:
    """Stands in for a real call to Keycloak: hands back our own throwaway public key."""
    with patch.object(routes, "_jwks_client") as mock_client:
        signing_key = types.SimpleNamespace(key=PRIVATE_KEY.public_key())
        mock_client.return_value.get_signing_key_from_jwt.return_value = signing_key
        yield


def test_a_genuinely_signed_token_is_accepted():
    token = _token(PRIVATE_KEY, workspaces=["test_workspace"])

    headers = routes.extract_headers(_credentials(token))

    assert headers["X-Authenticated"] is True
    assert headers["X-Workspaces"] == ["test_workspace"]


def test_a_forged_signature_is_rejected():
    """This is the exact bug that shipped: verify_signature was False, so any signature -
    including one that is not cryptographically valid at all - was accepted.
    """
    header = jwt.utils.base64url_encode(b'{"alg":"RS256","typ":"JWT"}').decode()
    payload = jwt.utils.base64url_encode(
        b'{"sub":"attacker","preferred_username":"attacker","workspaces":["test_workspace"],"aud":"account"}'
    ).decode()
    forged_signature = jwt.utils.base64url_encode(b"not-a-real-signature").decode()
    forged_token = f"{header}.{payload}.{forged_signature}"

    with pytest.raises(HTTPException) as raised:
        routes.extract_headers(_credentials(forged_token))

    assert raised.value.status_code == 401


def test_a_token_signed_by_a_different_key_is_rejected():
    """Guards against accepting any valid-looking signature rather than specifically
    Keycloak's: a token signed end-to-end correctly, just with the wrong key.
    """
    other_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    token = _token(other_key, workspaces=["test_workspace"])

    with pytest.raises(HTTPException) as raised:
        routes.extract_headers(_credentials(token))

    assert raised.value.status_code == 401


def test_the_wrong_audience_is_rejected():
    """A genuinely signed token issued for a different client should not be accepted."""
    token = _token(PRIVATE_KEY, aud="some-other-client", workspaces=["test_workspace"])

    with pytest.raises(HTTPException) as raised:
        routes.extract_headers(_credentials(token))

    assert raised.value.status_code == 401


def test_no_token_returns_unauthenticated_headers():
    headers = routes.extract_headers(None)

    assert headers == {"X-Workspaces": [], "X-Authenticated": False}


class TestAuthorizeWorkspace:
    """Covers the write-side IDOR: `workspace` on transaction request models (PostItem,
    PutItem, ...) is a client-supplied path/query field, not derived from the verified
    token, so it must be checked against X-Workspaces (built from the token) before a
    write is allowed to proceed.
    """

    def test_a_workspace_the_token_grants_is_allowed(self):
        headers = {"X-Workspaces": ["test_workspace"]}
        routes._authorize_workspace("test_workspace", headers)

    def test_a_workspace_the_token_does_not_grant_is_rejected(self):
        """The core exploit: an attacker who owns no workspaces (or a different one) sets
        `workspace` on the request to someone else's workspace.
        """
        headers = {"X-Workspaces": ["test_workspace"]}
        with pytest.raises(HTTPException) as raised:
            routes._authorize_workspace("someone_elses_workspace", headers)

        assert raised.value.status_code == 403

    def test_an_unauthenticated_caller_is_rejected(self):
        with pytest.raises(HTTPException) as raised:
            routes._authorize_workspace("test_workspace", {"X-Workspaces": []})

        assert raised.value.status_code == 403

    def test_a_request_with_no_workspace_field_is_a_noop(self):
        """Not every request model carries a `workspace` field (e.g. read endpoints), so
        None must not be rejected."""
        routes._authorize_workspace(None, {"X-Workspaces": []})
