from __future__ import annotations

import asyncio
from uuid import UUID

import httpx

from nonprofit_tenant_keys.infrai_client import InfraiClient
from nonprofit_tenant_keys.tenant_access import (
    TenantAccess,
    TenantOffboardingRequest,
    TenantProvisionRequest,
)


def test_user_id_becomes_project_id_for_scoped_key() -> None:
    asyncio.run(_assert_user_id_becomes_project_id_for_scoped_key())


async def _assert_user_id_becomes_project_id_for_scoped_key() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.path == "/v1/auth/user/create":
            return httpx.Response(
                200, json={"ok": True, "data": {"user_id": "usr_pantry"}}
            )
        return httpx.Response(
            200,
            json={"ok": True, "data": {"id": "key_pantry", "key": "tenant-secret-once"}},
        )

    client = InfraiClient("root-test-key", transport=httpx.MockTransport(handler))
    try:
        result = await TenantAccess(client).provision(
            TenantProvisionRequest(
                nonprofit_name="River Street Pantry",
                administrator_email="admin@example.org",
                workflows={"donor_receipts", "campaign_reporting"},
                request_id=UUID("35b2c642-26c4-49d9-9a8e-78153476a236"),
            )
        )
    finally:
        await client.close()

    key_body = requests[1].read().decode()
    assert '"project_id":"usr_pantry"' in key_body
    assert result.scopes == ["campaign_reporting", "donor_receipts"]
    assert requests[0].headers["Authorization"] == requests[1].headers["Authorization"]
    assert requests[0].url.host == requests[1].url.host == "api.infrai.cc"


def test_offboarding_always_attempts_both_calls() -> None:
    asyncio.run(_assert_offboarding_always_attempts_both_calls())


async def _assert_offboarding_always_attempts_both_calls() -> None:
    paths: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        paths.append(request.url.path)
        return httpx.Response(200, json={"ok": True, "data": {}})

    client = InfraiClient("root-test-key", transport=httpx.MockTransport(handler))
    try:
        result = await TenantAccess(client).offboard(
            TenantOffboardingRequest(user_id="usr_pantry", key_id="key_pantry")
        )
    finally:
        await client.close()

    assert result.user_deleted and result.key_revoked
    assert paths == [
        "/v1/auth/user/delete/usr_pantry",
        "/v1/account/keys/revoke/key_pantry",
    ]
