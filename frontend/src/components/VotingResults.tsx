import type { Ballot, Principal } from "../types";

interface Props {
  ballots: Ballot[];
  principals: Principal[];
  winnerId?: string;
}

export function VotingResults({ ballots, principals, winnerId }: Props) {
  return (
    <div className="voting-results">
      <h3>Voting Results</h3>
      <table>
        <thead>
          <tr>
            <th>Delegate</th>
            <th>Ranking (best → worst)</th>
          </tr>
        </thead>
        <tbody>
          {ballots.map((b) => {
            const idx = parseInt(b.delegate_id.replace("D", ""), 10);
            const principal = principals[idx];
            return (
              <tr key={b.delegate_id}>
                <td>
                  <strong>{principal?.name ?? b.delegate_id}</strong>
                </td>
                <td>
                  {b.ranking.map((sid, i) => (
                    <span
                      key={i}
                      className={`rank-chip ${sid === winnerId ? "rank-winner" : ""}`}
                    >
                      {sid}
                    </span>
                  ))}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
