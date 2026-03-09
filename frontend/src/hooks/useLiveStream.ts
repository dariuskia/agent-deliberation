import { useEffect, useRef, useState } from "react";
import type {
  Ballot,
  CandidateStatement,
  DeliberationResult,
  Message,
  Phase,
  Principal,
  SatisfactionScore,
} from "../types";

export function useLiveStream(sessionId: string | undefined) {
  const [result, setResult] = useState<Partial<DeliberationResult>>({});
  const [phase, setPhase] = useState<Phase>("idle");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const esRef = useRef<EventSource | null>(null);

  useEffect(() => {
    if (!sessionId) return;

    const es = new EventSource(`/api/deliberate/${sessionId}/stream`);
    esRef.current = es;
    setPhase("started");

    es.addEventListener("started", (e) => {
      const data = JSON.parse(e.data);
      setResult({
        question: data.question,
        principals: data.principals as Principal[],
        rounds: [],
        candidate_statements: [],
        ballots: [],
        satisfaction_scores: {},
        metadata: {},
      });
      setPhase("deliberating");
    });

    es.addEventListener("round_complete", (e) => {
      const data = JSON.parse(e.data);
      setResult((prev) => ({
        ...prev,
        rounds: [...(prev.rounds || []), data.messages as Message[]],
      }));
    });

    es.addEventListener("statements_complete", (e) => {
      const data = JSON.parse(e.data);
      setResult((prev) => ({
        ...prev,
        candidate_statements: data.candidate_statements as CandidateStatement[],
      }));
      setPhase("voting");
    });

    es.addEventListener("voting_complete", (e) => {
      const data = JSON.parse(e.data);
      setResult((prev) => ({
        ...prev,
        ballots: data.ballots as Ballot[],
        winner: data.winner as CandidateStatement,
      }));
      setPhase("satisfaction");
    });

    es.addEventListener("satisfaction_complete", (e) => {
      const data = JSON.parse(e.data);
      setResult((prev) => ({
        ...prev,
        satisfaction_scores: data.satisfaction_scores as Record<string, SatisfactionScore>,
      }));
    });

    es.addEventListener("done", () => {
      setPhase("done");
      es.close();
    });

    es.addEventListener("error", (e: Event) => {
      const me = e as MessageEvent;
      if (me.data) {
        try {
          const data = JSON.parse(me.data);
          setErrorMessage(data.message || "Unknown error");
        } catch {
          setErrorMessage(me.data);
        }
      } else {
        setErrorMessage("Connection lost");
      }
      setPhase("error");
      es.close();
    });

    return () => es.close();
  }, [sessionId]);

  return { result, phase, errorMessage };
}
