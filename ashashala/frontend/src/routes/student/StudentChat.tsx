import { useEffect, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { streamChat } from "../../api/client";
import { studentApi } from "../../api/endpoints";
import type { Citation } from "../../types/api";
import { PageTitle } from "../../components/layout/AppLayout";
import { Button, Card, Input, Spinner } from "../../components/ui";
import { CitationList } from "../../components/citations/ClickableCitation";
import { VoiceInputButton } from "../../components/voice/VoiceInputButton";
import { TTSToggle, speak } from "../../components/voice/TTSPlayer";
import { useVoice } from "../../stores/voice";

interface Msg {
  role: "user" | "assistant";
  content: string;
  citations?: Citation[];
}

export default function StudentChat() {
  const classes = useQuery({ queryKey: ["student", "classes"], queryFn: studentApi.classes });
  const [classId, setClassId] = useState<string>("");
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<Msg[]>([]);
  const [streaming, setStreaming] = useState(false);
  const ttsEnabled = useVoice((s) => s.ttsEnabled);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!classId && classes.data?.class_ids?.length) setClassId(classes.data.class_ids[0]);
  }, [classes.data, classId]);

  useEffect(() => {
    scrollRef.current?.scrollTo(0, scrollRef.current.scrollHeight);
  }, [messages]);

  const send = async (question: string) => {
    if (!question.trim() || !classId || streaming) return;
    setInput("");
    setMessages((m) => [...m, { role: "user", content: question }, { role: "assistant", content: "" }]);
    setStreaming(true);

    let full = "";
    await streamChat(
      { question, class_id: classId },
      {
        onToken: (t) => {
          full += t;
          setMessages((m) => {
            const copy = [...m];
            copy[copy.length - 1] = { role: "assistant", content: full };
            return copy;
          });
        },
        onCitations: (c) => {
          setMessages((m) => {
            const copy = [...m];
            copy[copy.length - 1] = { ...copy[copy.length - 1], citations: c as Citation[] };
            return copy;
          });
        },
        onError: (msg) => {
          setMessages((m) => {
            const copy = [...m];
            copy[copy.length - 1] = { role: "assistant", content: `⚠ ${msg}` };
            return copy;
          });
        },
        onDone: () => {
          setStreaming(false);
          if (ttsEnabled && full) speak(full);
        },
      },
    );
  };

  return (
    <div className="flex flex-col h-[calc(100vh-3rem)]">
      <div className="flex items-center justify-between">
        <PageTitle subtitle="Ask anything about your class materials — text or voice.">Tutor Chat</PageTitle>
        <div className="flex items-center gap-2">
          <TTSToggle />
          {classes.data && (
            <select
              className="text-sm border border-slate-300 rounded-lg px-2 py-1"
              value={classId}
              onChange={(e) => setClassId(e.target.value)}
            >
              {classes.data.class_ids.map((c) => (
                <option key={c} value={c}>
                  {c.slice(0, 8)}
                </option>
              ))}
            </select>
          )}
        </div>
      </div>

      <Card className="flex-1 flex flex-col min-h-0 mt-2">
        <div ref={scrollRef} className="flex-1 overflow-y-auto p-5 space-y-4">
          {messages.length === 0 && (
            <p className="text-center text-slate-400 mt-10">
              Try: “Explain fractions with an example” or ask in Gujarati / Hindi.
            </p>
          )}
          {messages.map((m, i) => (
            <div key={i} className={m.role === "user" ? "text-right" : "text-left"}>
              <div
                className={`inline-block max-w-[80%] px-4 py-2 rounded-2xl text-sm whitespace-pre-wrap ${
                  m.role === "user" ? "bg-brand-600 text-white" : "bg-slate-100 text-slate-800"
                }`}
              >
                {m.content || (streaming && i === messages.length - 1 ? <Spinner /> : "")}
              </div>
              {m.role === "assistant" && m.citations && (
                <div className="max-w-[80%]">
                  <CitationList citations={m.citations} />
                </div>
              )}
            </div>
          ))}
        </div>

        <form
          className="border-t border-slate-100 p-3 flex gap-2"
          onSubmit={(e) => {
            e.preventDefault();
            send(input);
          }}
        >
          <VoiceInputButton onTranscript={(t) => send(t)} />
          <Input
            placeholder="Ask your tutor…"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            disabled={streaming}
          />
          <Button type="submit" disabled={streaming || !input.trim()}>
            Send
          </Button>
        </form>
      </Card>
    </div>
  );
}
