"""RAG job execution with retrieval citations and optional evaluation.

No generative LLM is used here. The answer is intentionally extractive and
explicitly labeled to avoid misrepresenting retrieval as a model-generated answer.
"""
import json
from .rag_client import retrieve, evaluate_answer

async def execute_rag(job: dict) -> str:
    evidence = await retrieve(job["prompt"], str(job["tenant_id"]))
    if evidence:
        answer = evidence[0]["text"]
        mode = "extractive_first_chunk"
    else:
        answer = "Insufficient retrieved evidence to answer."
        mode = "insufficient_evidence"
    result = {
        "mode": mode,
        "answer": answer,
        "citations": [{"source": hit["source"], "chunk_id": hit["chunk_id"]} for hit in evidence],
        "evaluation": None,
    }
    if job.get("reference_answer") is not None:
        result["evaluation"] = await evaluate_answer(
            answer, job["reference_answer"], str(job["id"])
        )
    return json.dumps(result, ensure_ascii=False)
