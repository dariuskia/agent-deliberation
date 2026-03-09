import type { Principal } from "../types";
import { DELEGATE_COLORS } from "./colors";

interface Props {
  delegateId: string;
  content: string;
  principal?: Principal;
  colorIndex: number;
}

export function MessageBubble({ delegateId, content, principal, colorIndex }: Props) {
  const color = DELEGATE_COLORS[colorIndex % DELEGATE_COLORS.length];

  return (
    <div className="message-bubble" style={{ borderLeftColor: color }}>
      <div className="message-header">
        <span className="avatar-sm" style={{ background: color }}>
          {principal?.name[0] ?? "?"}
        </span>
        <strong>{principal?.name ?? delegateId}</strong>
        <span className="delegate-badge">{delegateId}</span>
      </div>
      <div className="message-content">{content}</div>
    </div>
  );
}
