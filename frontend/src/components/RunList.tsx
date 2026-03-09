import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { fetchRuns } from "../api";
import type { RunSummary } from "../types";

export function RunList() {
  const [runs, setRuns] = useState<RunSummary[]>([]);
  const { id } = useParams();

  useEffect(() => {
    fetchRuns().then(setRuns);
  }, []);

  return (
    <div className="run-list">
      <h3>Past Runs</h3>
      {runs.length === 0 && <p className="empty">No runs yet</p>}
      {runs.map((r) => (
        <Link
          key={r.id}
          to={`/run/${r.id}`}
          className={`run-item ${r.id === id ? "active" : ""}`}
        >
          <div className="run-timestamp">{r.timestamp}</div>
          <div className="run-question">{r.question.slice(0, 60)}...</div>
        </Link>
      ))}
    </div>
  );
}
