import type { Principal } from "../types";
import { DELEGATE_COLORS } from "./colors";

interface Props {
  principals: Principal[];
}

export function PrincipalCards({ principals }: Props) {
  return (
    <div className="principal-cards">
      {principals.map((p, i) => (
        <div
          key={p.id}
          className="principal-card"
          style={{ borderLeftColor: DELEGATE_COLORS[i % DELEGATE_COLORS.length] }}
        >
          <div className="card-header">
            <span
              className="avatar"
              style={{ background: DELEGATE_COLORS[i % DELEGATE_COLORS.length] }}
            >
              {p.name[0]}
            </span>
            <strong>{p.name}</strong>
            <span className="delegate-badge">D{i}</span>
          </div>
          <p className="profile">{p.profile}</p>
          <p className="values">{p.values}</p>
          {p.hidden_values && (
            <details className="hidden-values">
              <summary>Hidden Values</summary>
              <p>{p.hidden_values}</p>
            </details>
          )}
        </div>
      ))}
    </div>
  );
}
