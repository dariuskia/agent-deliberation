import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { Principal, SatisfactionScore } from "../types";

interface Props {
  scores: Record<string, SatisfactionScore>;
  principals: Principal[];
}

function scoreColor(score: number): string {
  if (score >= 7) return "#4caf50";
  if (score >= 4) return "#ff9800";
  return "#f44336";
}

export function SatisfactionChart({ scores, principals }: Props) {
  const data = principals.map((p) => ({
    name: p.name.split(" ")[0],
    score: scores[p.id]?.score ?? 0,
    reasoning: scores[p.id]?.reasoning ?? "",
    fullName: p.name,
  }));

  const avg = data.reduce((s, d) => s + d.score, 0) / data.length;

  return (
    <div className="satisfaction-chart">
      <h3>
        Satisfaction Scores{" "}
        <span className="avg-badge">avg: {avg.toFixed(1)}/10</span>
      </h3>
      <ResponsiveContainer width="100%" height={300}>
        <BarChart data={data} layout="vertical" margin={{ left: 80 }}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis type="number" domain={[0, 10]} />
          <YAxis type="category" dataKey="name" width={80} />
          <Tooltip
            formatter={(_: unknown, __: unknown, props: { payload: { reasoning: string } }) => [
              props.payload.reasoning,
              "Reasoning",
            ]}
            labelFormatter={(_: unknown, payload: Array<{ payload: { fullName: string } }>) =>
              payload[0]?.payload.fullName ?? ""
            }
          />
          <Bar dataKey="score" radius={[0, 4, 4, 0]}>
            {data.map((d, i) => (
              <Cell key={i} fill={scoreColor(d.score)} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
