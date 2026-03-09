import type { CandidateStatement, Principal } from "../types";
import { DELEGATE_COLORS } from "./colors";

interface Props {
  statements: CandidateStatement[];
  winnerId?: string;
  principals: Principal[];
}

export function StatementsPanel({ statements, winnerId, principals }: Props) {
  return (
    <div className="statements-panel">
      <h3>Candidate Consensus Statements</h3>
      {statements.map((s) => {
        const idx = parseInt(s.delegate_id.replace("D", ""), 10);
        const principal = principals[idx];
        const isWinner = s.id === winnerId;

        return (
          <div
            key={s.id}
            className={`statement-card ${isWinner ? "winner" : ""}`}
            style={{ borderLeftColor: DELEGATE_COLORS[idx % DELEGATE_COLORS.length] }}
          >
            <div className="statement-header">
              <span className="statement-id">{s.id}</span>
              <span className="statement-author">by {principal?.name ?? s.delegate_id}</span>
              {isWinner && <span className="winner-badge">Winner</span>}
            </div>
            <p>{s.text}</p>
          </div>
        );
      })}
    </div>
  );
}
