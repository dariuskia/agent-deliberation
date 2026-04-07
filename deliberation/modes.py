"""Three deliberation modes: centralized, clustered, and delegates."""

from .deliberation import run_deliberation
from .llm import LLMClient, extract_json
from .models import (
    Ballot,
    CandidateStatement,
    DeliberationResult,
    Message,
    Principal,
)
from .prompts import (
    ballot_prompt,
    candidate_synthesis_prompt,
    cluster_assignment_prompt,
    initial_statement_prompt,
    mediator_feedback_prompt,
    mediator_prompt,
)
from .scoring import score_satisfaction
from .voting import instant_runoff


async def run_centralized(
    llm: LLMClient,
    principals: list[Principal],
    question: str,
    num_rounds: int = 3,
    label: str = "centralized",
) -> DeliberationResult:
    """Centralized: single AI mediator drafts consensus, principals give feedback iteratively."""

    # Phase 1: Initial statements from each principal
    print(f"  [{label}] Collecting initial statements...")
    stmt_requests = [initial_statement_prompt(p, question) for p in principals]
    stmt_responses = await llm.complete_batch(stmt_requests)

    statements = [
        (p.name, resp.strip()) for p, resp in zip(principals, stmt_responses)
    ]
    all_messages = [
        Message(round_num=0, delegate_id=f"D{i}", content=resp.strip())
        for i, resp in enumerate(stmt_responses)
    ]

    # Phase 2: Iterative mediator drafts + principal feedback
    draft = ""
    feedback = None
    for round_num in range(1, num_rounds + 1):
        print(f"  [{label}] Round {round_num}/{num_rounds}...")

        # Mediator generates/revises draft
        sys_msg, usr_msg = mediator_prompt(question, statements, feedback)
        draft = (await llm.complete(sys_msg, usr_msg, temperature=0.5)).strip()

        all_messages.append(
            Message(round_num=round_num, delegate_id="mediator", content=draft)
        )

        # Principals provide feedback (skip on last round)
        if round_num < num_rounds:
            fb_requests = [
                mediator_feedback_prompt(p, question, draft) for p in principals
            ]
            fb_responses = await llm.complete_batch(fb_requests)
            feedback = [
                (p.name, resp.strip())
                for p, resp in zip(principals, fb_responses)
            ]
            for i, resp in enumerate(fb_responses):
                all_messages.append(
                    Message(
                        round_num=round_num,
                        delegate_id=f"D{i}",
                        content=resp.strip(),
                    )
                )

    # Phase 3: Final consensus — mediator's last draft is the winner
    winner = CandidateStatement(id="S0", delegate_id="mediator", text=draft)

    # Phase 4: Satisfaction scoring
    print(f"  [{label}] Scoring satisfaction...")
    satisfaction = await score_satisfaction(llm, principals, question, winner)

    rounds_grouped = []
    for r in range(num_rounds + 1):
        rounds_grouped.append([m for m in all_messages if m.round_num == r])

    return DeliberationResult(
        question=question,
        principals=principals,
        rounds=rounds_grouped,
        candidate_statements=[winner],
        ballots=[],
        winner=winner,
        satisfaction_scores=satisfaction,
    )


async def run_clustered(
    llm: LLMClient,
    principals: list[Principal],
    question: str,
    n_clusters: int = 3,
    num_rounds: int = 3,
    label: str = "clustered",
) -> DeliberationResult:
    """Clustered: principals' positions are clustered, AI candidates deliberate, principals vote."""

    n_clusters = min(n_clusters, len(principals))

    # Phase 1: Initial statements from each principal
    print(f"  [{label}] Collecting initial statements...")
    stmt_requests = [initial_statement_prompt(p, question) for p in principals]
    stmt_responses = await llm.complete_batch(stmt_requests)

    delegate_statements = [
        (f"D{i}", resp.strip()) for i, resp in enumerate(stmt_responses)
    ]

    # Phase 2: LLM assigns statements to clusters
    print(f"  [{label}] Clustering into {n_clusters} groups...")
    sys_msg, usr_msg = cluster_assignment_prompt(
        question, delegate_statements, n_clusters
    )
    cluster_response = await llm.complete(sys_msg, usr_msg, temperature=0.3)
    cluster_map = extract_json(cluster_response)  # {"D0": 0, "D1": 1, ...}

    # Group statements by cluster
    clusters: dict[int, list[tuple[str, str]]] = {}
    for did, text in delegate_statements:
        cid = cluster_map.get(did, 0)
        clusters.setdefault(cid, []).append((did, text))

    # Phase 3: Synthesize a candidate platform for each cluster
    print(f"  [{label}] Synthesizing candidate platforms...")
    synth_requests = []
    cluster_ids = sorted(clusters.keys())
    for cid in cluster_ids:
        sys_msg, usr_msg = candidate_synthesis_prompt(
            question, clusters[cid], cid
        )
        synth_requests.append((sys_msg, usr_msg))

    synth_responses = await llm.complete_batch(synth_requests, temperature=0.5)

    # Create synthetic candidate Principals
    candidate_principals = []
    for i, (cid, platform) in enumerate(zip(cluster_ids, synth_responses)):
        member_names = [
            principals[int(did[1:])].name
            for did, _ in clusters[cid]
        ]
        candidate_principals.append(
            Principal(
                id=f"C{cid}",
                name=f"Candidate {cid} (representing {', '.join(member_names)})",
                profile=f"AI candidate representing a coalition of participants who share similar views on this question.",
                values=platform.strip(),
            )
        )

    # Phase 4: Candidates deliberate among themselves (reuse delegate deliberation)
    print(f"  [{label}] Candidates deliberating ({len(candidate_principals)} candidates, {num_rounds} rounds)...")
    candidate_result = await run_deliberation(
        llm=llm,
        principals=candidate_principals,
        question=question,
        num_rounds=num_rounds,
        include_hidden_values=False,
        label=f"{label}/candidates",
    )

    # Phase 5: Real principals vote on candidate consensus statements
    print(f"  [{label}] Principals voting on candidate proposals...")
    ballot_requests = []
    for p in principals:
        sys_msg, usr_msg = ballot_prompt(
            p, question, candidate_result.candidate_statements, [],
            include_hidden_values=False,
        )
        ballot_requests.append((sys_msg, usr_msg))

    ballot_responses = await llm.complete_batch(ballot_requests, temperature=0.3)

    ballots = []
    for i, (p, resp) in enumerate(zip(principals, ballot_responses)):
        ranking = extract_json(resp)
        ballots.append(Ballot(delegate_id=f"D{i}", ranking=ranking))

    winner = instant_runoff(ballots, candidate_result.candidate_statements)
    print(f"  [{label}] Winner: {winner.id}")

    # Phase 6: Satisfaction scoring
    print(f"  [{label}] Scoring satisfaction...")
    satisfaction = await score_satisfaction(llm, principals, question, winner)

    return DeliberationResult(
        question=question,
        principals=principals,
        rounds=candidate_result.rounds,
        candidate_statements=candidate_result.candidate_statements,
        ballots=ballots,
        winner=winner,
        satisfaction_scores=satisfaction,
    )


async def run_delegates(
    llm: LLMClient,
    principals: list[Principal],
    question: str,
    num_rounds: int = 3,
    label: str = "delegates",
) -> DeliberationResult:
    """Delegates: each principal has a dedicated AI agent (existing system)."""
    return await run_deliberation(
        llm=llm,
        principals=principals,
        question=question,
        num_rounds=num_rounds,
        include_hidden_values=False,
        label=label,
    )
