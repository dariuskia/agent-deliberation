from dataclasses import dataclass, field


@dataclass
class Principal:
    id: str
    name: str
    profile: str
    values: str
    hidden_values: str = ""


@dataclass
class Delegate:
    id: str
    principal: Principal


@dataclass
class Message:
    round_num: int
    delegate_id: str
    content: str


@dataclass
class CandidateStatement:
    id: str
    delegate_id: str
    text: str


@dataclass
class Ballot:
    delegate_id: str
    ranking: list[str]  # Statement IDs, most-preferred first


@dataclass
class DeliberationResult:
    question: str
    principals: list[Principal]
    rounds: list[list[Message]]
    candidate_statements: list[CandidateStatement]
    ballots: list[Ballot]
    winner: CandidateStatement
    satisfaction_scores: dict[str, dict]  # principal_id -> {score, reasoning}
    metadata: dict = field(default_factory=dict)


@dataclass
class ExperimentResult:
    config: dict
    delegate_result: DeliberationResult
    principal_result: DeliberationResult
    delegation_regret: dict  # per-principal and aggregate regret metrics
