from .llm import LLMClient, extract_json
from .models import CandidateStatement, Principal
from .prompts import satisfaction_prompt


async def score_satisfaction(
    llm: LLMClient,
    principals: list[Principal],
    question: str,
    winner: CandidateStatement,
) -> dict[str, dict]:
    requests = [satisfaction_prompt(p, question, winner) for p in principals]
    responses = await llm.complete_batch(requests, temperature=0.3)

    scores = {}
    for principal, response in zip(principals, responses):
        parsed = extract_json(response)
        scores[principal.id] = {
            "score": parsed["score"],
            "reasoning": parsed["reasoning"],
        }
    return scores
