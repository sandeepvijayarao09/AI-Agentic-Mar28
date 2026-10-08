"use client";

import { useState, useRef, useEffect } from "react";

interface Message {
  role: "user" | "assistant";
  content: string;
}

export function SecondBrainChat() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const sendMessage = async () => {
    if (!input.trim() || loading) return;
    const userMsg: Message = { role: "user", content: input.trim() };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setLoading(true);

    try {
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: userMsg.content, history: [] }),
      });
      const data = await res.json();
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: data.response || data.detail || "Something went wrong." },
      ]);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: "Error connecting to backend. Make sure the server is running." },
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="h-screen flex flex-col bg-[#0a0a0a]">
      {/* Header */}
      <header className="border-b border-gray-800 px-6 py-4 flex items-center justify-between bg-black/80 backdrop-blur-sm">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-full bg-gradient-to-br from-purple-500 to-blue-500 flex items-center justify-center text-white font-bold text-lg shadow-lg shadow-purple-500/20">
            SB
          </div>
          <div>
            <h1 className="text-xl font-bold text-white">Agentic Second Brain</h1>
            <p className="text-xs text-gray-400">
              Powered by Google ADK + Gemini
            </p>
          </div>
        </div>
        <div className="flex gap-2">
          <StatusButton />
          <SyncButton />
        </div>
      </header>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 py-6">
        <div className="max-w-3xl mx-auto space-y-4">
          {messages.length === 0 && (
            <div className="text-center text-gray-500 mt-20">
              <div className="text-6xl mb-4">🧠</div>
              <h2 className="text-2xl font-semibold text-gray-300 mb-2">
                Your Agentic Second Brain
              </h2>
              <p className="text-gray-500 mb-6">
                I know your food orders, shopping history, and favourites from Gmail.
              </p>
              <div className="flex flex-wrap gap-2 justify-center">
                {[
                  "What are my favourite restaurants?",
                  "I want to order food",
                  "Show my recent Amazon orders",
                  "Sync my emails",
                ].map((suggestion) => (
                  <button
                    key={suggestion}
                    onClick={() => { setInput(suggestion); }}
                    className="px-4 py-2 rounded-full bg-gray-800 hover:bg-gray-700 text-sm text-gray-300 transition-colors"
                  >
                    {suggestion}
                  </button>
                ))}
              </div>
            </div>
          )}

          {messages.map((msg, i) => (
            <div key={i} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
              <div
                className={`max-w-[80%] rounded-2xl px-4 py-3 ${
                  msg.role === "user"
                    ? "bg-blue-600 text-white"
                    : "bg-gray-800 text-gray-100"
                }`}
              >
                <div className="whitespace-pre-wrap text-sm leading-relaxed" dangerouslySetInnerHTML={{
                  __html: msg.content
                    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
                    .replace(/\[(.+?)\]\((.+?)\)/g, '<a href="$2" target="_blank" class="text-blue-400 underline">$1</a>')
                    .replace(/\n/g, "<br/>")
                }} />
              </div>
            </div>
          ))}

          {loading && (
            <div className="flex justify-start">
              <div className="bg-gray-800 rounded-2xl px-4 py-3">
                <div className="flex gap-1">
                  <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: "0ms" }} />
                  <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: "150ms" }} />
                  <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: "300ms" }} />
                </div>
              </div>
            </div>
          )}
          <div ref={bottomRef} />
        </div>
      </div>

      {/* Input */}
      <div className="border-t border-gray-800 bg-black/80 backdrop-blur-sm px-4 py-4">
        <div className="max-w-3xl mx-auto flex gap-2">
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && sendMessage()}
            placeholder="Ask about your orders, favourites, or anything..."
            className="flex-1 bg-gray-800 text-white px-4 py-3 rounded-xl border border-gray-700 focus:border-blue-500 focus:outline-none placeholder-gray-500"
            disabled={loading}
          />
          <button
            onClick={sendMessage}
            disabled={loading || !input.trim()}
            className="px-6 py-3 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-700 disabled:cursor-not-allowed text-white rounded-xl font-medium transition-colors"
          >
            Send
          </button>
        </div>
      </div>
    </div>
  );
}

function SyncButton() {
  const handleSync = async () => {
    try {
      const res = await fetch("/api/sync/gmail", { method: "POST" });
      const data = await res.json();
      alert(`Synced! Food: ${data.food_synced || 0}, Shopping: ${data.shopping_synced || 0}`);
    } catch {
      alert("Sync failed — make sure Gmail is connected");
    }
  };
  return (
    <button onClick={handleSync} className="px-3 py-1.5 text-sm bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors">
      Sync Gmail
    </button>
  );
}

function StatusButton() {
  const handleCheck = async () => {
    try {
      const res = await fetch("/api/auth/gmail/status");
      const data = await res.json();
      if (data.authenticated) {
        const stats = await fetch("/api/sync/stats").then((r) => r.json());
        alert(`Gmail: Connected\nFood: ${stats.food_orders}\nShopping: ${stats.shopping_orders}\nFavourites: ${stats.favourites}`);
      } else {
        if (confirm("Gmail not connected. Connect now?")) {
          window.location.href = "/api/auth/gmail/authorize";
        }
      }
    } catch {
      alert("Backend not reachable");
    }
  };
  return (
    <button onClick={handleCheck} className="px-3 py-1.5 text-sm bg-gray-700 hover:bg-gray-600 text-white rounded-lg transition-colors">
      Status
    </button>
  );
}
