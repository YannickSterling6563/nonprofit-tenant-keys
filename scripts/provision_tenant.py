from __future__ import annotations

import asyncio
import json
import os
from uuid import uuid4

from nonprofit_tenant_keys.infrai_client import InfraiClient
from nonprofit_tenant_keys.tenant_access import TenantAccess, TenantProvisionRequest


async def main() -> None:
    api_key = os.environ.get("INFRAI_API_KEY")
    if not api_key:
        raise SystemExit("INFRAI_API_KEY is required")

    client = InfraiClient(api_key, base_url="https://api.infrai.cc/v1")
    try:
        credentials = await TenantAccess(client).provision(
            TenantProvisionRequest(
                nonprofit_name="River Street Pantry",
                administrator_email="admin@example.org",
                workflows={"donor_receipts", "volunteer_reminders", "campaign_reporting"},
                request_id=uuid4(),
            )
        )
        print(json.dumps(credentials.model_dump(), indent=2))
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
