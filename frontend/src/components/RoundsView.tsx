import type { Message, Principal } from "../types";
import { MessageBubble } from "./MessageBubble";

interface Props {
  rounds: Message[][];
  principals: Principal[];
}

export function RoundsView({ rounds, principals }: Props) {
  const principalMap = Object.fromEntries(principals.map((p, i) => [`D${i}`, { principal: p, index: i }]));

  return (
    <div className="rounds-view">
      <h3>Deliberation Rounds</h3>
      {rounds.map((messages, i) => (
        <details key={i} open={i === rounds.length - 1}>
          <summary>Round {i + 1} ({messages.length} messages)</summary>
          <div className="round-messages">
            {messages.map((m, j) => (
              <MessageBubble
                key={j}
                delegateId={m.delegate_id}
                content={m.content}
                principal={principalMap[m.delegate_id]?.principal}
                colorIndex={principalMap[m.delegate_id]?.index ?? 0}
              />
            ))}
          </div>
        </details>
      ))}
    </div>
  );
}
