import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { fetchConfig, startDeliberation } from "../api";

export function LaunchForm() {
  const [question, setQuestion] = useState("");
  const [numRounds, setNumRounds] = useState(3);
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    fetchConfig().then((c) => {
      setQuestion(c.question);
      setNumRounds(c.num_rounds);
    });
  }, []);

  const handleLaunch = async () => {
    setLoading(true);
    try {
      const { session_id } = await startDeliberation(question, numRounds);
      setLoading(false);
      navigate(`/live/${session_id}`);
    } catch {
      setLoading(false);
    }
  };

  return (
    <div className="launch-form">
      <h3>Launch New Deliberation</h3>
      <label>
        Question
        <textarea
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          rows={3}
        />
      </label>
      <label>
        Rounds
        <input
          type="number"
          min={1}
          max={10}
          value={numRounds}
          onChange={(e) => setNumRounds(Number(e.target.value))}
        />
      </label>
      <button onClick={handleLaunch} disabled={loading || !question}>
        {loading ? "Starting..." : "Start Deliberation"}
      </button>
    </div>
  );
}
