import { BrowserRouter, Route, Routes, useParams } from "react-router-dom";
import { Layout } from "./components/Layout";
import { LiveStatus } from "./components/LiveStatus";
import { PrincipalCards } from "./components/PrincipalCards";
import { RoundsView } from "./components/RoundsView";
import { SatisfactionChart } from "./components/SatisfactionChart";
import { StatementsPanel } from "./components/StatementsPanel";
import { SummaryBanner } from "./components/SummaryBanner";
import { VotingResults } from "./components/VotingResults";
import { useDeliberation } from "./hooks/useDeliberation";
import { useLiveStream } from "./hooks/useLiveStream";
import type { DeliberationResult } from "./types";

function RunView() {
  const { id } = useParams();
  const { data, loading, error } = useDeliberation(id);

  if (loading) return <p>Loading...</p>;
  if (error) return <p className="error">Error: {error}</p>;
  if (!data) return <p className="empty">Select a run from the sidebar</p>;

  return <ResultDisplay result={data} />;
}

function LiveView() {
  const { sessionId } = useParams();
  const { result, phase, errorMessage } = useLiveStream(sessionId);

  return (
    <div>
      <LiveStatus
        phase={phase}
        roundCount={result.rounds?.length ?? 0}
        errorMessage={errorMessage}
      />
      {result.question && (
        <ResultDisplay result={result as DeliberationResult} partial />
      )}
    </div>
  );
}

function ResultDisplay({
  result,
  partial = false,
}: {
  result: DeliberationResult;
  partial?: boolean;
}) {
  return (
    <div className="result-display">
      <SummaryBanner
        question={result.question}
        winner={result.winner}
        satisfactionScores={result.satisfaction_scores}
      />

      {result.principals?.length > 0 && (
        <PrincipalCards principals={result.principals} />
      )}

      {result.rounds?.length > 0 && (
        <RoundsView rounds={result.rounds} principals={result.principals} />
      )}

      {result.candidate_statements?.length > 0 && (
        <StatementsPanel
          statements={result.candidate_statements}
          winnerId={result.winner?.id}
          principals={result.principals}
        />
      )}

      {result.ballots?.length > 0 && (
        <VotingResults
          ballots={result.ballots}
          principals={result.principals}
          winnerId={result.winner?.id}
        />
      )}

      {result.satisfaction_scores &&
        Object.keys(result.satisfaction_scores).length > 0 && (
          <SatisfactionChart
            scores={result.satisfaction_scores}
            principals={result.principals}
          />
        )}

      {partial && !result.winner && (
        <p className="waiting">Waiting for more data...</p>
      )}
    </div>
  );
}

function Home() {
  return <p className="empty">Launch a new deliberation or select a past run.</p>;
}

export default function App() {
  return (
    <BrowserRouter>
      <Layout>
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/run/:id" element={<RunView />} />
          <Route path="/live/:sessionId" element={<LiveView />} />
        </Routes>
      </Layout>
    </BrowserRouter>
  );
}
