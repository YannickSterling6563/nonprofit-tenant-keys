from __future__ import annotations

import os

from fastapi import FastAPI, HTTPException

from .infrai_client import InfraiClient, InfraiError
from .tenant_access import (
    OffboardingError,
    TenantAccess,
    TenantCredentials,
    TenantOffboardingRequest,
    TenantOffboardingResult,
    TenantProvisionRequest,
)

app = FastAPI(title="Nonprofit tenant access")


def tenant_access() -> TenantAccess:
    api_key = os.environ.get("INFRAI_API_KEY")
    if not api_key:
        raise RuntimeError("INFRAI_API_KEY is required")
    return TenantAccess(InfraiClient(api_key))


@app.post("/tenants", response_model=TenantCredentials)
async def provision_tenant(request: TenantProvisionRequest) -> TenantCredentials:
    access = tenant_access()
    try:
        return await access.provision(request)
    except InfraiError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    finally:
        await access.infrai.close()


@app.delete("/tenants/access", response_model=TenantOffboardingResult)
async def offboard_tenant(request: TenantOffboardingRequest) -> TenantOffboardingResult:
    access = tenant_access()
    try:
        return await access.offboard(request)
    except OffboardingError as exc:
        status_code = max(failure.status_code for failure in exc.failures)
        detail = [failure.detail for failure in exc.failures]
        raise HTTPException(status_code=status_code, detail=detail) from exc
    finally:
        await access.infrai.close()
