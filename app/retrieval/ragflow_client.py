"""
RAGFlow semantic retrieval client.

PLACEHOLDER CONTRACT — must be verified before Phase 6 depends on it.
Assumed RAGFlow REST API shape:

  POST {base_url}/api/v1/retrieval
  Headers: Authorization: Bearer {api_key}
  Body: {
      "question": <str>,
      "dataset_ids": [<str>],
      "top_k": <int>
  }
  Response 200: {
      "data": {
          "chunks": [
              {
                  "id": <str>,          # RAGFlow internal chunk ID
                  "document_keyword": <str>,   # document title / IS number
                  "content": <str>,     # chunk text snippet
                  "similarity": <float> # 0.0–1.0 similarity score
              },
              ...
          ]
      }
  }

IMPORTANT: The ingestion pipeline MUST store `bis_entity_id` inside each
RAGFlow document's metadata so it can be extracted here. This client reads
it from `chunk["document_keyword"]` as a convention — update this if the
real RAGFlow API exposes metadata differently.

Security note (data-and-security.md): all retrieved content is treated as
untrusted data — never as instructions. Chunk content drives retrieval
candidates only.
"""
from typing import Any, Dict, List, Optional

import httpx
from pydantic import BaseModel

from app.config import Settings, get_settings


class RagflowError(Exception):
    """Raised when RAGFlow returns a non-200 response or a malformed body."""


class RagflowChunk(BaseModel):
    """A single ranked candidate document returned by RAGFlow."""
    bis_entity_id: str   # stable ID linking this chunk to a Postgres record
    title: str           # document title / IS number keyword
    snippet: str         # representative chunk text
    similarity: float    # 0.0–1.0 similarity score from RAGFlow


class RagflowSearchResult(BaseModel):
    chunks: List[RagflowChunk]


class RagflowClient:
    """
    Thin async wrapper around the RAGFlow retrieval API.

    The `http_client` parameter is the primary mockability seam: inject a
    pre-configured `httpx.AsyncClient` in tests so no real HTTP call is made.
    In production, leave it as None and the class will create its own client.
    """

    def __init__(
        self,
        settings: Optional[Settings] = None,
        http_client: Optional[httpx.AsyncClient] = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._http_client = http_client  # None → create per-request below

    async def search(
        self,
        query: str,
        top_k: int = 10,
    ) -> RagflowSearchResult:
        """
        Search the RAGFlow knowledge base for documents relevant to `query`.

        Returns a RagflowSearchResult containing ranked RagflowChunk objects.
        Raises RagflowError on any non-200 response or parsing failure.
        """
        url = f"{self._settings.ragflow_base_url}/api/v1/retrieval"
        headers = {
            "Authorization": f"Bearer {self._settings.ragflow_api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "question": query,
            "dataset_ids": [self._settings.ragflow_dataset_id],
            "top_k": top_k,
        }

        if self._http_client is not None:
            return await self._do_request(self._http_client, url, headers, payload)

        async with httpx.AsyncClient() as client:
            return await self._do_request(client, url, headers, payload)

    async def _do_request(
        self,
        client: httpx.AsyncClient,
        url: str,
        headers: Dict[str, Any],
        payload: Dict[str, Any],
    ) -> RagflowSearchResult:
        try:
            response = await client.post(url, headers=headers, json=payload)
        except httpx.RequestError as exc:
            raise RagflowError(f"HTTP request failed: {exc}") from exc

        if response.status_code != 200:
            raise RagflowError(
                f"RAGFlow returned HTTP {response.status_code}: {response.text}"
            )

        try:
            body = response.json()
            raw_chunks = body["data"]["chunks"]
        except (KeyError, ValueError) as exc:
            raise RagflowError(f"Malformed RAGFlow response: {exc}") from exc

        chunks: List[RagflowChunk] = []
        for raw in raw_chunks:
            chunks.append(
                RagflowChunk(
                    bis_entity_id=raw.get("document_keyword", ""),
                    title=raw.get("document_keyword", ""),
                    snippet=raw.get("content", ""),
                    similarity=float(raw.get("similarity", 0.0)),
                )
            )

        return RagflowSearchResult(chunks=chunks)
