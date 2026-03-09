from .llm import LLMClient, extract_json
from .models import (
    Ballot,
    CandidateStatement,
    Delegate,
    DeliberationResult,
    Message,
    Principal,
)
from .prompts import ballot_prompt, candidate_statement_prompt, delegate_round_prompt
from .scoring import score_satisfaction
from .topology import FlatTopology
from .voting import instant_runoff


async def run_deliberation(
    llm: LLMClient,
    principals: list[Principal],
    question: str,
    num_rounds: int = 3,
    topology: FlatTopology | None = None,
    include_hidden_values: bool = False,
    label: str = "delegate",
) -> DeliberationResult:
    topology = topology or FlatTopology()
    delegates = [Delegate(id=f"D{i}", principal=p) for i, p in enumerate(principals)]
    all_messages: list[Message] = []

    # Phase 1: Deliberation rounds
    for round_num in range(1, num_rounds + 1):
        print(f"  [{label}] Round {round_num}/{num_rounds}...")
        requests = []
        for delegate in delegates:
            visible = topology.visible_messages(delegate.id, all_messages)
            system, user = delegate_round_prompt(
                delegate.principal, question, round_num, visible,
                include_hidden_values=include_hidden_values,
            )
            requests.append((system, user))

        responses = await llm.complete_batch(requests)

        for delegate, response in zip(delegates, responses):
            msg = Message(
                round_num=round_num, delegate_id=delegate.id, content=response
            )
            all_messages.append(msg)

    # Phase 2: Each delegate proposes a consensus statement
    print(f"  [{label}] Generating candidate statements...")
    statement_requests = []
    for delegate in delegates:
        system, user = candidate_statement_prompt(
            delegate.principal, question, all_messages,
            include_hidden_values=include_hidden_values,
        )
        statement_requests.append((system, user))

    statement_responses = await llm.complete_batch(statement_requests, temperature=0.5)

    candidates = []
    for i, (delegate, text) in enumerate(zip(delegates, statement_responses)):
        candidates.append(
            CandidateStatement(id=f"S{i}", delegate_id=delegate.id, text=text.strip())
        )

    # Phase 3: Delegates vote
    print(f"  [{label}] Voting...")
    ballot_requests = []
    for delegate in delegates:
        system, user = ballot_prompt(
            delegate.principal, question, candidates, all_messages,
            include_hidden_values=include_hidden_values,
        )
        ballot_requests.append((system, user))

    ballot_responses = await llm.complete_batch(ballot_requests, temperature=0.3)

    ballots = []
    for delegate, response in zip(delegates, ballot_responses):
        ranking = extract_json(response)
        ballots.append(Ballot(delegate_id=delegate.id, ranking=ranking))

    # Phase 4: Ranked-choice vote
    winner = instant_runoff(ballots, candidates)
    print(f"  [{label}] Winner: {winner.id}")

    # Phase 5: Satisfaction scoring (always uses full info including hidden values)
    print(f"  [{label}] Scoring satisfaction...")
    satisfaction = await score_satisfaction(llm, principals, question, winner)

    # Assemble result
    rounds_grouped = []
    for r in range(1, num_rounds + 1):
        rounds_grouped.append([m for m in all_messages if m.round_num == r])

    return DeliberationResult(
        question=question,
        principals=principals,
        rounds=rounds_grouped,
        candidate_statements=candidates,
        ballots=ballots,
        winner=winner,
        satisfaction_scores=satisfaction,
    )
