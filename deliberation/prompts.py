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
