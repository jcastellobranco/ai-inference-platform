"""Authenticated BFF for the private single-tenant RAG HTTP service.

The browser never receives service credentials. The tenant is always taken from
the verified JWT principal, then checked against the service's configured tenant.
"""
import os
from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel, Field

from .main import principal
from .rag_client import IntegrationConfigurationError, _service_settings

router = APIRouter(prefix="/v1/knowledge", tags=["knowledge"])
MAX_PDF_BYTES = 10 * 1024 * 1024


class TextDocument(BaseModel):
    source: str = Field(min_length=1, max_length=256)
    text: str = Field(min_length=1, max_length=200000)


class SearchRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    limit: int = Field(default=5, ge=1, le=20)


def _settings(identity: dict) -> tuple[str, dict[str, str]]:
    try:
        url, key, tenant = _service_settings(identity["tenant"])
    except PermissionError:
        raise HTTPException(403, "Knowledge base unavailable for this tenant")
    except (IntegrationConfigurationError, ValueError):
        raise HTTPException(503, "Knowledge base is not configured")
    return url, {"x-api-key": key, "x-tenant-id": tenant}


def _upstream(method: str, path: str, identity: dict, *,
              json_body: dict | None = None, files=None) -> dict:
    url, headers = _settings(identity)
    try:
        with httpx.Client(timeout=httpx.Timeout(120.0), trust_env=False) as client:
            response = client.request(method, f"{url}{path}", headers=headers,
                                      json=json_body, files=files)
        if response.status_code == 404:
            raise HTTPException(404, "Document not found")
        if response.status_code in (413, 415, 422):
            raise HTTPException(response.status_code, "Document rejected by knowledge service")
        if response.is_error:
            raise HTTPException(502, "Knowledge service request failed")
        return response.json()
    except httpx.RequestError:
        raise HTTPException(502, "Knowledge service unavailable")
    except ValueError:
        raise HTTPException(502, "Invalid knowledge service response")


@router.get("/documents")
def list_documents(identity=Depends(principal)):
    return _upstream("GET", "/v1/documents", identity)


@router.post("/documents", status_code=201)
def add_document(body: TextDocument, identity=Depends(principal)):
    if not body.source.strip() or not body.text.strip():
        raise HTTPException(422, "Document source and text must not be blank")
    return _upstream("POST", "/v1/documents", identity, json_body=body.model_dump())


@router.post("/documents/pdf", status_code=201)
def upload_pdf(file: UploadFile = File(...), identity=Depends(principal)):
    if file.content_type != "application/pdf":
        raise HTTPException(415, "Only PDFs are supported")
    raw = file.file.read(MAX_PDF_BYTES + 1)
    if len(raw) > MAX_PDF_BYTES:
        raise HTTPException(413, "PDF exceeds 10 MiB")
    if not raw.startswith(b"%PDF-"):
        raise HTTPException(422, "File does not appear to be a PDF")
    return _upstream("POST", "/v1/documents/pdf", identity,
                     files={"file": (file.filename or "upload.pdf", raw, "application/pdf")})


@router.delete("/documents/{document_id}")
def delete_document(document_id: UUID, identity=Depends(principal)):
    return _upstream("DELETE", f"/v1/documents/{document_id}", identity)


@router.post("/search")
def search(body: SearchRequest, identity=Depends(principal)):
    if not body.question.strip():
        raise HTTPException(422, "Question must not be blank")
    return _upstream("POST", "/v1/search", identity, json_body=body.model_dump())
