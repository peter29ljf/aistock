import type { ChatEvent, Strategy } from "./types";

async function j<T>(r: Response): Promise<T> {
  if (!r.ok) throw new Error(`${r.status} ${await r.text()}`);
  return r.json();
}

export const api = {
  listStrategies: () => fetch("/api/strategies").then(j<Strategy[]>),
  createStrategy: (name: string, description = "") =>
    fetch("/api/strategies", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ name, description }),
    }).then(j<Strategy>),
  deleteStrategy: (sid: string) =>
    fetch(`/api/strategies/${sid}`, { method: "DELETE" }).then(j<{ ok: boolean }>),
  getStrategy: (sid: string) => fetch(`/api/strategies/${sid}`).then(j<Strategy>),

  listAgentSessions: () => fetch("/api/agent").then(j<Strategy[]>),
  createAgentSession: (name = "") =>
    fetch("/api/agent", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ name }),
    }).then(j<Strategy>),
  deleteAgentSession: (sid: string) =>
    fetch(`/api/agent/${sid}`, { method: "DELETE" }).then(j<{ ok: boolean }>),

  sendMessage: (sid: string, message: string) =>
    fetch(`/api/strategies/${sid}/chat`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ message }),
    }).then(j<{ ok: boolean }>),
  loadHistory: (sid: string, limit = 200) =>
    fetch(`/api/strategies/${sid}/chat/history?limit=${limit}`).then(j<ChatEvent[]>),
};
