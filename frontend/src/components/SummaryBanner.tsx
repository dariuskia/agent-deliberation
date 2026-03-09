import type { CandidateStatement, SatisfactionScore } from "../types";

interface Props {
  question: string;
  winner?: CandidateStatement;
  satisfactionScores?: Record<string, SatisfactionScore>;
}

export function SummaryBanner({ question, winner, satisfactionScores }: Props) {
  const scores = satisfactionScores ? Object.values(satisfactionScores) : [];
  const avg = scores.length
    ? (scores.reduce((s, v) => s + v.score, 0) / scores.length).toFixed(1)
    : null;

  return (
    <div className="summary-banner">
      <h2>{question}</h2>
      {winner && (
        <div className="winner-statement">
          <span className="label">Winner:</span> {winner.text}
        </div>
      )}
      {avg && (
        <div className="avg-score">
          Average satisfaction: <strong>{avg}/10</strong>
        </div>
      )}
    </div>
  );
}
