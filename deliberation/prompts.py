from .models import CandidateStatement, Message, Principal


def _format_history(messages: list[Message]) -> str:
    if not messages:
        return ""
    lines = []
    for m in messages:
        lines.append(f"[{m.delegate_id}, Round {m.round_num}]:\n{m.content}")
    return "\n\n".join(lines)


def _hidden_section(principal: Principal, include: bool) -> str:
    if include and principal.hidden_values:
        return f"""

Their private, deeply-held values (things they would never say publicly but care about intensely):
{principal.hidden_values}"""
    return ""


def delegate_round_prompt(
    principal: Principal,
    question: str,
    round_num: int,
    history: list[Message],
    include_hidden_values: bool = False,
) -> tuple[str, str]:
    hidden = _hidden_section(principal, include_hidden_values)

    system = f"""You are a delegate in a structured deliberation. You represent a specific person \
and must advocate for their perspective while engaging constructively with others.

THE PERSON YOU REPRESENT:
{principal.profile}

Their values and worldview:
{principal.values}{hidden}

RULES:
- Argue from your principal's perspective, values, and interests.
- Engage with what others have said. You may agree, disagree, or build on points.
- Be concise (2-4 paragraphs max).
- Aim for productive dialogue, not just restating your position.
- You may shift emphasis based on the conversation, but stay true to your principal's core values."""

    history_text = _format_history(history)

    if history_text:
        user = f"""QUESTION FOR DELIBERATION: {question}

ROUND {round_num} OF DISCUSSION.

CONVERSATION SO FAR:
{history_text}

Now provide your contribution for round {round_num}."""
    else:
        user = f"""QUESTION FOR DELIBERATION: {question}

ROUND {round_num} OF DISCUSSION.

This is the opening round. State your principal's initial position on the question."""

    return system, user


def candidate_statement_prompt(
    principal: Principal,
    question: str,
    history: list[Message],
    include_hidden_values: bool = False,
) -> tuple[str, str]:
    hidden = _hidden_section(principal, include_hidden_values)

    system = f"""You are a delegate who has just finished a multi-round deliberation. \
You represent a specific person and must now propose a consensus statement that you believe \
the group could accept — while still honoring your principal's core values.

THE PERSON YOU REPRESENT:
{principal.profile}

Their values and worldview:
{principal.values}{hidden}

INSTRUCTIONS:
- Propose a single consensus statement (1-3 sentences) that reflects the deliberation.
- It should be a statement the broadest possible coalition could endorse.
- It must not betray your principal's core values, but can incorporate others' concerns.
- Output ONLY the consensus statement text, nothing else."""

    user = f"""QUESTION: {question}

FULL DELIBERATION TRANSCRIPT:
{_format_history(history)}

Propose your consensus statement now."""

    return system, user


def ballot_prompt(
    principal: Principal,
    question: str,
    candidates: list[CandidateStatement],
    history: list[Message],
    include_hidden_values: bool = False,
) -> tuple[str, str]:
    hidden = _hidden_section(principal, include_hidden_values)

    system = f"""You are voting on behalf of the person you represent.

THE PERSON YOU REPRESENT:
{principal.profile}

Their views:
{principal.values}{hidden}

Rank ALL candidate consensus statements from most to least preferred, considering:
- How well it aligns with your principal's values and interests
- Whether the deliberation surfaced good arguments for it

Output ONLY a JSON array of statement IDs in order, best first. Example: ["S2", "S0", "S1", "S3"]"""

    candidates_text = "\n".join(f"  {c.id}: {c.text}" for c in candidates)

    user = f"""QUESTION: {question}

CANDIDATE CONSENSUS STATEMENTS:
{candidates_text}

Rank them now."""

    return system, user


def initial_statement_prompt(
    principal: Principal,
    question: str,
) -> tuple[str, str]:
    system = f"""You are participating in a public deliberation process. You represent a specific person \
and must state their position clearly and concisely.

THE PERSON YOU REPRESENT:
{principal.profile}

Their values and worldview:
{principal.values}

RULES:
- State your principal's position on the question in 1-3 paragraphs.
- Be clear about what matters most to them and why.
- This is a public statement — express only what they would say publicly."""

    user = f"""QUESTION: {question}

Write your initial position statement."""

    return system, user


def mediator_prompt(
    question: str,
    statements: list[tuple[str, str]],
    feedback: list[tuple[str, str]] | None = None,
) -> tuple[str, str]:
    system = """You are a neutral AI mediator tasked with producing a consensus statement \
that best represents all participant perspectives. You must balance competing viewpoints \
and find common ground while acknowledging key tensions.

INSTRUCTIONS:
- Read all participant statements and any feedback on prior drafts.
- Produce a single consensus statement (2-4 sentences) that the broadest coalition could accept.
- Address specific feedback if provided.
- Output ONLY the consensus statement text, nothing else."""

    statements_text = "\n\n".join(
        f"[{name}]: {text}" for name, text in statements
    )
    user = f"""QUESTION: {question}

PARTICIPANT STATEMENTS:
{statements_text}"""

    if feedback:
        feedback_text = "\n\n".join(
            f"[{name}]: {text}" for name, text in feedback
        )
        user += f"""

FEEDBACK ON PREVIOUS DRAFT:
{feedback_text}

Revise the consensus statement to address this feedback."""

    return system, user


def mediator_feedback_prompt(
    principal: Principal,
    question: str,
    draft_consensus: str,
) -> tuple[str, str]:
    system = f"""You are providing feedback on a draft consensus statement on behalf of a specific person.

THE PERSON YOU REPRESENT:
{principal.profile}

Their values and worldview:
{principal.values}

RULES:
- Evaluate the draft consensus from your principal's perspective.
- Identify what works and what's missing or unacceptable.
- Suggest specific improvements. Be concise (1-2 paragraphs)."""

    user = f"""QUESTION: {question}

DRAFT CONSENSUS STATEMENT:
{draft_consensus}

Provide your feedback."""

    return system, user


def cluster_assignment_prompt(
    question: str,
    statements: list[tuple[str, str]],
    n_clusters: int,
) -> tuple[str, str]:
    system = f"""You are an analyst grouping participant positions into {n_clusters} clusters \
based on similarity of their stance on the question.

INSTRUCTIONS:
- Read all statements and identify {n_clusters} distinct position clusters.
- Assign each participant to exactly one cluster.
- Output ONLY a JSON object mapping participant IDs to cluster numbers (0-indexed).
- Example: {{"D0": 0, "D1": 1, "D2": 0, "D3": 2}}"""

    statements_text = "\n\n".join(
        f"[{did}]: {text}" for did, text in statements
    )

    user = f"""QUESTION: {question}

PARTICIPANT STATEMENTS:
{statements_text}

Assign each participant to one of {n_clusters} clusters."""

    return system, user


def candidate_synthesis_prompt(
    question: str,
    cluster_statements: list[tuple[str, str]],
    cluster_id: int,
) -> tuple[str, str]:
    system = """You are synthesizing a group of similar positions into a single coherent platform.

INSTRUCTIONS:
- Read all statements from this constituency.
- Produce a concise platform (2-3 paragraphs) that captures the shared values and priorities.
- This platform will be used as the identity of an AI candidate who will deliberate on behalf of this group.
- Output ONLY the platform text, nothing else."""

    statements_text = "\n\n".join(
        f"[{did}]: {text}" for did, text in cluster_statements
    )

    user = f"""QUESTION: {question}

CONSTITUENCY STATEMENTS (Cluster {cluster_id}):
{statements_text}

Synthesize these into a single platform."""

    return system, user


def satisfaction_prompt(
    principal: Principal,
    question: str,
    winner: CandidateStatement,
) -> tuple[str, str]:
    hidden = _hidden_section(principal, True)  # always include hidden values

    system = f"""You are simulating this person's reaction to a deliberation outcome:

{principal.profile}

Their views:
{principal.values}{hidden}

Score your satisfaction with the consensus statement on a scale of 1-10, considering BOTH
their public values AND their private, deeply-held values.
1 = completely unacceptable, 10 = perfectly represents my views.
Output ONLY a JSON object: {{"score": <int>, "reasoning": "<brief explanation>"}}"""

    user = f"""QUESTION: {question}

THE WINNING CONSENSUS STATEMENT:
{winner.text}

How satisfied is this person with this outcome?"""

    return system, user
