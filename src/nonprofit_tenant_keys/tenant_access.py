from __future__ import annotations

from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from .infrai_client import InfraiClient, InfraiError


class NonprofitWorkflow(StrEnum):
    DONOR_RECEIPTS = "donor_receipts"
    VOLUNTEER_REMINDERS = "volunteer_reminders"
    CAMPAIGN_REPORTING = "campaign_reporting"


class TenantProvisionRequest(BaseModel):
    nonprofit_name: str = Field(min_length=1)
    administrator_email: str = Field(min_length=3, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    workflows: set[NonprofitWorkflow] = Field(min_length=1)
    request_id: UUID


class TenantCredentials(BaseModel):
    user_id: str
    key_id: str
    api_key: str
    scopes: list[str]


class TenantOffboardingRequest(BaseModel):
    user_id: str = Field(min_length=1)
    key_id: str = Field(min_length=1)


class TenantOffboardingResult(BaseModel):
    user_deleted: bool
    key_revoked: bool


class OffboardingError(Exception):
    def __init__(self, failures: list[InfraiError]) -> None:
        super().__init__("offboarding did not complete")
        self.failures = failures


class TenantAccess:
    def __init__(self, infrai: InfraiClient) -> None:
        self.infrai = infrai

    async def provision(self, request: TenantProvisionRequest) -> TenantCredentials:
        user = await self.infrai.request(
            "POST",
            "/auth/user/create",
            json={
                "email": str(request.administrator_email),
                "name": request.nonprofit_name,
                "metadata": {"tenant": request.nonprofit_name},
                "idempotency_key": f"{request.request_id}:user",
            },
        )
        user_id = self._required_string(user, "user_id", "user")
        scopes = sorted(workflow.value for workflow in request.workflows)
        key = await self.infrai.request(
            "POST",
            "/account/keys/create",
            json={
                "project_id": user_id,
                "name": f"{request.nonprofit_name} tenant key",
                "scopes": scopes,
                "idempotency_key": f"{request.request_id}:key",
            },
        )
        return TenantCredentials(
            user_id=user_id,
            key_id=self._required_id(key, "key"),
            api_key=self._required_string(key, "key"),
            scopes=scopes,
        )

    async def offboard(self, request: TenantOffboardingRequest) -> TenantOffboardingResult:
        failures: list[InfraiError] = []
        user_deleted = await self._complete_or_record(
            "DELETE", f"/auth/user/delete/{request.user_id}", failures
        )
        key_revoked = await self._complete_or_record(
            "DELETE", f"/account/keys/revoke/{request.key_id}", failures
        )
        if failures:
            raise OffboardingError(failures)
        return TenantOffboardingResult(user_deleted=user_deleted, key_revoked=key_revoked)

    async def _complete_or_record(
        self, method: str, path: str, failures: list[InfraiError]
    ) -> bool:
        try:
            await self.infrai.request(method, path)
            return True
        except InfraiError as exc:
            failures.append(exc)
            return False

    @staticmethod
    def _required_id(data: dict[str, Any], label: str) -> str:
        return TenantAccess._required_string(data, "id", label)

    @staticmethod
    def _required_string(data: dict[str, Any], field: str, label: str = "response") -> str:
        value = data.get(field)
        if not isinstance(value, str) or not value:
            raise ValueError(f"{label} response did not contain {field}")
        return value
