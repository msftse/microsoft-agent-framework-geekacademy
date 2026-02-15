"""Memory store management — create/get memory store for agent conversations.

Uses Azure AI Projects client to create a memory store with chat summary
and user profile capabilities.  The memory store persists across server
restarts (create is idempotent — returns existing store if name matches).
"""

from __future__ import annotations

from azure.ai.projects.aio import AIProjectClient
from azure.ai.projects.models import (
    MemoryStoreDefaultDefinition,
    MemoryStoreDefaultOptions,
)
from azure.core.credentials_async import AsyncTokenCredential


async def ensure_memory_store(
    endpoint: str,
    credential: AsyncTokenCredential,
    store_name: str,
    chat_model: str,
    embedding_model: str,
) -> str | None:
    """Create the memory store if it doesn't already exist.

    Returns the memory store name on success, or None if creation fails
    (e.g. missing embedding model deployment).  This allows the server to
    start without memory when the required models aren't deployed.
    """
    try:
        async with AIProjectClient(
            endpoint=endpoint, credential=credential
        ) as project_client:
            # Try to get existing store first
            try:
                existing = await project_client.memory_stores.get(store_name)
                print(f"[memory] Using existing memory store: {existing.name}")
                return existing.name
            except Exception:
                pass  # Store doesn't exist yet, create it

            definition = MemoryStoreDefaultDefinition(
                chat_model=chat_model,
                embedding_model=embedding_model,
                options=MemoryStoreDefaultOptions(
                    user_profile_enabled=True,
                    chat_summary_enabled=True,
                ),
            )

            store = await project_client.memory_stores.create(
                name=store_name,
                description="Memory store for Geektime content pipeline agents",
                definition=definition,
            )
            print(f"[memory] Created memory store: {store.name} ({store.id})")
            return store.name
    except Exception as exc:
        print(f"[memory] Failed to create memory store: {exc}")
        print(
            "[memory] Continuing without agent memory — deploy an embedding model to enable"
        )
        return None
