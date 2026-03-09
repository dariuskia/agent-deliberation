import asyncio
import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from deliberation.llm import LLMClient, extract_json
from deliberation.models import (
    Ballot,
    CandidateStatement,
    Delegate,
    DeliberationResult,
    Message,
    Principal,
)
from deliberation.prompts import ballot_prompt, candidate_statement_prompt, delegate_round_prompt
from deliberation.scoring import score_satisfaction
from deliberation.topology import FlatTopology
from deliberation.voting import instant_runoff


async def run_deliberation_streaming(
    llm: LLMClient,
    principals: list[Principal],
    question: str,
    num_rounds: int,
    event_queue: asyncio.Queue,
    runs_dir: Path,
):
    """Mirrors deliberation.deliberation.run_deliberation but emits SSE events."""
    topology = FlatTopology()
    delegates = [Delegate(id=f"D{i}", principal=p) for i, p in enumerate(principals)]
    all_messages: list[Message] = []

    try:
        await event_queue.put(
            {
                "type": "started",
                "data": {
                    "question": question,
                    "num_rounds": num_rounds,
                    "principals": [asdict(p) for p in principals],
                },
            }
        )

        # Phase 1: Deliberation rounds
        for round_num in range(1, num_rounds + 1):
            requests = []
            for delegate in delegates:
                visible = topology.visible_messages(delegate.id, all_messages)
                system, user = delegate_round_prompt(
                    delegate.principal, question, round_num, visible
                )
                requests.append((system, user))

            responses = await llm.complete_batch(requests)

            round_messages = []
            for delegate, response in zip(delegates, responses):
                msg = Message(round_num=round_num, delegate_id=delegate.id, content=response)
                all_messages.append(msg)
                round_messages.append(msg)

            await event_queue.put(
                {
                    "type": "round_complete",
                    "data": {
                        "round_num": round_num,
                        "messages": [asdict(m) for m in round_messages],
                    },
                }
            )

        # Phase 2: Candidate statements
        statement_requests = []
        for delegate in delegates:
            system, user = candidate_statement_prompt(delegate.principal, question, all_messages)
            statement_requests.append((system, user))

        statement_responses = await llm.complete_batch(statement_requests, temperature=0.5)

        candidates = []
        for i, (delegate, text) in enumerate(zip(delegates, statement_responses)):
            candidates.append(
                CandidateStatement(id=f"S{i}", delegate_id=delegate.id, text=text.strip())
            )

        await event_queue.put(
            {
                "type": "statements_complete",
                "data": {"candidate_statements": [asdict(c) for c in candidates]},
            }
        )

        # Phase 3: Voting
        ballot_requests = []
        for delegate in delegates:
            system, user = ballot_prompt(delegate.principal, question, candidates, all_messages)
            ballot_requests.append((system, user))

        ballot_responses = await llm.complete_batch(ballot_requests, temperature=0.3)

        ballots = []
        for delegate, response in zip(delegates, ballot_responses):
            ranking = extract_json(response)
            ballots.append(Ballot(delegate_id=delegate.id, ranking=ranking))

        # Phase 4: IRV
        winner = instant_runoff(ballots, candidates)

        await event_queue.put(
            {
                "type": "voting_complete",
                "data": {
                    "ballots": [asdict(b) for b in ballots],
                    "winner": asdict(winner),
                },
            }
        )

        # Phase 5: Satisfaction
        satisfaction = await score_satisfaction(llm, principals, question, winner)

        await event_queue.put(
            {
                "type": "satisfaction_complete",
                "data": {"satisfaction_scores": satisfaction},
            }
        )

        # Save result
        rounds_grouped = []
        for r in range(1, num_rounds + 1):
            rounds_grouped.append([m for m in all_messages if m.round_num == r])

        result = DeliberationResult(
            question=question,
            principals=principals,
            rounds=rounds_grouped,
            candidate_statements=candidates,
            ballots=ballots,
            winner=winner,
            satisfaction_scores=satisfaction,
        )

        runs_dir.mkdir(exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        run_id = f"{timestamp}_result"
        output_path = runs_dir / f"{run_id}.json"
        with open(output_path, "w") as f:
            json.dump(asdict(result), f, indent=2)

        await event_queue.put({"type": "done", "data": {"run_id": run_id}})

    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        await event_queue.put({"type": "error", "data": {"message": f"{e}\n{tb}"}})
