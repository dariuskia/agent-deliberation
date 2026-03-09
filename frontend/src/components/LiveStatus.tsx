import type { Phase } from "../types";

interface Props {
  phase: Phase;
  roundCount: number;
  totalRounds?: number;
  errorMessage?: string | null;
}

const PHASE_LABELS: Record<Phase, string> = {
  idle: "Waiting...",
  started: "Starting deliberation...",
  deliberating: "Deliberating...",
  statements: "Generating consensus statements...",
  voting: "Voting...",
  satisfaction: "Scoring satisfaction...",
  done: "Complete",
  error: "Error occurred",
};

export function LiveStatus({ phase, roundCount, totalRounds, errorMessage }: Props) {
  const label =
    phase === "deliberating"
      ? `Round ${roundCount}${totalRounds ? ` of ${totalRounds}` : ""} complete`
      : phase === "error" && errorMessage
        ? `Error: ${errorMessage}`
        : PHASE_LABELS[phase];

  return (
    <div className={`live-status phase-${phase}`}>
      {phase !== "done" && phase !== "error" && <span className="spinner" />}
      <span>{label}</span>
    </div>
  );
}
