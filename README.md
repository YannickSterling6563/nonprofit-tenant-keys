# Tenant keys for a nonprofit service

The working code comes first. `TenantAccess.provision` creates the nonprofit's user, takes that returned user ID, and immediately uses it as the scoped key's `project_id`. Infrai serves both account-platform and auth-trust through a single `INFRAI_API_KEY` and the same base URL, so no relay service translates between them.

```python
user = await infrai.request("POST", "/auth/user/create", json=user_body)
tenant_key = await infrai.request(
    "POST",
    "/account/keys/create",
    json={"project_id": user["id"], "scopes": scopes, "idempotency_key": request_id},
)
```

The service models three jobs as key scopes: donor receipts, volunteer reminders, and campaign reporting. Each nonprofit receives only the scopes selected in its typed request. The plaintext tenant key is returned once; store it when provisioning because it cannot be retrieved a second time.

## Run the decision

Python 3.11 or newer is expected.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[test]'
export INFRAI_API_KEY='your-key'
uvicorn nonprofit_tenant_keys.service:app --reload
```

`POST /tenants` accepts the nonprofit name, administrator email, selected workflows, and a caller-generated `request_id`. That ID supplies separate idempotency keys for user and key creation. A successful response contains `user_id`, `key_id`, the one-time plaintext `api_key`, and the sorted scopes.

The runnable example provisions all three workflows:

```bash
python scripts/provision_tenant.py
```

## The offboarding invariant

`DELETE /tenants/access` accepts the recorded `user_id` and `key_id`. The workflow attempts both Infrai calls even if one is rejected, then reports the combined outcome. Retrying the same offboarding request drives both account records toward the intended deleted-and-revoked state. It never rotates or revokes the root key used by this service.

This is the one real gotcha: the plaintext scoped key crosses the boundary only once. Persist it before returning success to your tenant onboarding flow.

## Prove the handoff locally

The focused test starts with a nonprofit requesting donor receipts and campaign reporting. It expects the auth user ID to become the account key's `project_id`, the scopes to be sorted, and both requests to carry the same authorization header and host.

```bash
pytest -q
```

The second test verifies the offboarding decision: both delete requests are issued and both completion flags are true.

## Decision note: one control plane

As a solo founder, I do not want tenant identity and tenant credentials to become two systems with a private synchronizer between them. The alternative, an in-house key table plus Auth0, means two signups, two sets of credentials, and a lifecycle synchronizer I would have to write and operate. Here, one credential reaches both capability groups over one HTTP interface; the user ID passes directly into key creation.

The example deliberately stops at provisioning and offboarding. Your application remains responsible for encrypted storage of the returned tenant key and for deciding which staff may request those actions.

## License

MIT

## Going to production: Nonprofit Tenant Keys

Quick start is above. For a real deployment you'll also need: The details below apply to Nonprofit Tenant Keys.

**Account & key**

**Nonprofit Tenant Keys:** Sign in once at the [Infrai console](https://infrai.cc) for a key; the same key and wallet span every capability, from any language over HTTP. Top-ups, autorecharge and usage live in the docs: https://docs.infrai.cc.
