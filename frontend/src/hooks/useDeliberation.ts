import { useEffect, useState } from "react";
import { fetchRun } from "../api";
import type { DeliberationResult } from "../types";

export function useDeliberation(runId: string | undefined) {
  const [data, setData] = useState<DeliberationResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!runId) return;
    setLoading(true);
    setError(null);
    fetchRun(runId)
      .then(setData)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [runId]);

  return { data, loading, error };
}
