"""Credential-optional provider clients with bounded retries and resumable pagination."""

import asyncio
import hashlib
import hmac
import json
import time
from typing import ClassVar

import httpx


class ProviderError(RuntimeError):
    pass


async def request(client, method, url, **kwargs):
    for attempt in range(5):
        response = await client.request(method, url, **kwargs)
        if response.status_code == 429 or response.status_code >= 500:
            if attempt == 4:
                response.raise_for_status()
            try:
                delay = min(
                    30, max(1, float(response.headers.get("Retry-After", 2**attempt)))
                )
            except ValueError:
                delay = 2**attempt
            await asyncio.sleep(delay)
            continue
        response.raise_for_status()
        return response.json()
    raise ProviderError("Retry limit reached")


class HubSpot:
    objects: ClassVar[set[str]] = {
        "companies",
        "contacts",
        "deals",
        "calls",
        "emails",
        "meetings",
        "notes",
        "tasks",
    }

    def __init__(self, token: str, base_url="https://api.hubapi.com", transport=None):
        if not token:
            raise ProviderError("HubSpot token is not configured")
        self.client = httpx.AsyncClient(
            base_url=base_url,
            headers={"Authorization": "Bearer " + token},
            timeout=30,
            transport=transport,
        )

    async def records(self, entity, properties=None, after=None, archived=False):
        if entity not in self.objects:
            raise ValueError("Unsupported CRM object")
        while True:
            params = {"limit": 100, "archived": str(archived).lower()}
            if after:
                params["after"] = after
            if properties:
                params["properties"] = ",".join(properties)
            data = await request(
                self.client, "GET", f"/crm/v3/objects/{entity}", params=params
            )
            yield (
                data.get("results", []),
                data.get("paging", {}).get("next", {}).get("after"),
            )
            after = data.get("paging", {}).get("next", {}).get("after")
            if not after:
                break

    async def pipelines(self):
        return await request(self.client, "GET", "/crm/v3/pipelines/deals")

    async def owners(self):
        return await request(
            self.client, "GET", "/crm/v3/owners", params={"limit": 100}
        )

    async def properties(self, entity):
        return await request(self.client, "GET", f"/crm/v3/properties/{entity}")

    async def close(self):
        await self.client.aclose()


class Stripe:
    entities: ClassVar[set[str]] = {
        "customers",
        "subscriptions",
        "invoices",
        "payment_intents",
        "refunds",
        "credit_notes",
    }

    def __init__(self, token: str, base_url="https://api.stripe.com", transport=None):
        if not token:
            raise ProviderError("Stripe API key is not configured")
        self.client = httpx.AsyncClient(
            base_url=base_url,
            headers={"Authorization": "Bearer " + token},
            timeout=30,
            transport=transport,
        )

    async def records(self, entity, starting_after=None, created_gte=None):
        if entity not in self.entities:
            raise ValueError("Unsupported Stripe entity")
        while True:
            params = {"limit": 100}
            if starting_after:
                params["starting_after"] = starting_after
            if created_gte is not None:
                params["created[gte]"] = created_gte
            result = await request(self.client, "GET", "/v1/" + entity, params=params)
            data = result.get("data", [])
            cursor = data[-1]["id"] if data and result.get("has_more") else None
            yield data, cursor
            if not cursor:
                break
            starting_after = cursor

    async def invoice_lines(self, invoice_id):
        return await request(
            self.client,
            "GET",
            f"/v1/invoices/{invoice_id}/lines",
            params={"limit": 100},
        )

    async def close(self):
        await self.client.aclose()


def verify_stripe_webhook(
    body: bytes, signature: str, secret: str, now=None, tolerance=300
):
    if not secret:
        raise ProviderError("Webhook signing secret is not configured")
    parts = [item.split("=", 1) for item in signature.split(",") if "=" in item]
    timestamp = next((int(v) for k, v in parts if k == "t"), 0)
    if abs((now or time.time()) - timestamp) > tolerance:
        raise ProviderError("Webhook signature timestamp outside tolerance")
    expected = hmac.new(
        secret.encode(), str(timestamp).encode() + b"." + body, hashlib.sha256
    ).hexdigest()
    if not any(k == "v1" and hmac.compare_digest(v, expected) for k, v in parts):
        raise ProviderError("Invalid webhook signature")
    return json.loads(body)
