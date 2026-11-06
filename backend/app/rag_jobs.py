"""Tenant-bound RAG execution with explicit answer states and retrieval diagnostics."""
import json
import os
from time import perf_counter
from .generation import generate_answer
from .rag_client import retrieve, evaluate_answer

async def execute_rag(job: dict) -> str:
    started = perf_counter()
    evidence = await retrieve(job["prompt"], str(job["tenant_id"]))
    model = None
    usage = None
    retrieval = {"chunks_found": len(evidence),
                 "sources": list(dict.fromkeys(hit["source"] for hit in evidence)),
                 "chunk_ids": [hit["chunk_id"] for hit in evidence]}
    if not evidence:
        answer = "Insufficient retrieved evidence to answer."
        mode = "insufficient_evidence"
    elif os.getenv("RAG_GENERATION_ENABLED", "false").lower() == "true":
        generated = await generate_answer(job["prompt"], evidence)
        answer = generated["answer"]
        mode = "grounded_generation" if generated["citation_numbers"] else "insufficient_evidence"
        model = generated["model"]
        usage = generated.get("usage")
        evidence = [evidence[index - 1] for index in generated["citation_numbers"]]
    else:
        answer = evidence[0]["text"]
        mode = "extractive_first_chunk"
    result = {
        "mode": mode,
        "answer_status": ("insufficient_evidence" if mode == "insufficient_evidence" else "answered"),
        "retrieval": retrieval,
        "answer": answer,
        "citations": [{"source": hit["source"], "chunk_id": hit["chunk_id"]} for hit in evidence],
        "evaluation": None,
        "model": model,
        "usage": usage,
    }
    if job.get("reference_answer") is not None:
        result["evaluation"] = await evaluate_answer(
            answer, job["reference_answer"], str(job["id"]),
            latency_ms=(perf_counter() - started) * 1000
        )
    return json.dumps(result, ensure_ascii=False)
