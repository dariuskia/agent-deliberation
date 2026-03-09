export interface Principal {
  id: string;
  name: string;
  profile: string;
  values: string;
  hidden_values: string;
}

export interface Message {
  round_num: number;
  delegate_id: string;
  content: string;
}

export interface CandidateStatement {
  id: string;
  delegate_id: string;
  text: string;
}

export interface Ballot {
  delegate_id: string;
  ranking: string[];
}

export interface SatisfactionScore {
  score: number;
  reasoning: string;
}

export interface DeliberationResult {
  question: string;
  principals: Principal[];
  rounds: Message[][];
  candidate_statements: CandidateStatement[];
  ballots: Ballot[];
  winner: CandidateStatement;
  satisfaction_scores: Record<string, SatisfactionScore>;
  metadata: Record<string, unknown>;
}

export interface RunSummary {
  id: string;
  timestamp: string;
  question: string;
}

export interface Config {
  question: string;
  model: string;
  num_rounds: number;
  principals: Principal[];
}

export type Phase =
  | "idle"
  | "started"
  | "deliberating"
  | "statements"
  | "voting"
  | "satisfaction"
  | "done"
  | "error";
