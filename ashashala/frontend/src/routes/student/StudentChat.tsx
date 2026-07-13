import { useEffect, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { streamChat } from "../../api/client";
import { studentApi } from "../../api/endpoints";
import type { Citation } from "../../types/api";
import { PageTitle } from "../../components/layout/AppLayout";
import { Card, Select } from "../../components/ui";
import { CitationList } from "../../components/citations/ClickableCitation";
import { VoiceInputButton } from "../../components/voice/VoiceInputButton";
import { TTSToggle, speak } from "../../components/voice/TTSPlayer";
import { useVoice } from "../../stores/voice";

interface Msg {
  role: "user" | "assistant";
  content: string;
  citations?: Citation[];
}

const SUGGESTIONS = [
  "Explain fractions with an example",
  "અપૂર્ણાંક શું છે?",
  "Why isn't 1/2 + 1/3 = 2/5?",
];

export default function StudentChat() {
  const { t } = useTranslation();
  const classes = useQuery({ queryKey: ["student", "classes"], queryFn: studentApi.classes });
  const [classId, setClassId] = useState("");
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<Msg[]>([]);
  const [streaming, setStreaming] = useState(false);
  const ttsEnabled = useVoice((s) => s.ttsEnabled);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!classId && classes.data?.class_ids?.length) setClassId(classes.data.class_ids[0]);
  }, [classes.data, classId]);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
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
    <div className="flex flex-col h-[calc(100vh-7rem)]">
      <div className="flex items-start justify-between flex-wrap gap-3">
        <PageTitle subtitle={t("student.chat.subtitle")}>
          {t("student.chat.title")}
        </PageTitle>
        <div className="flex items-center gap-2">
          <TTSToggle />
          {classes.data && classes.data.class_ids.length > 0 && (
            <Select value={classId} onChange={(e) => setClassId(e.target.value)} className="w-auto py-2">
              {classes.data.class_ids.map((c) => (
                <option key={c} value={c}>
                  {t("student.chat.classLabel", { id: c.slice(0, 6) })}
                </option>
              ))}
            </Select>
          )}
        </div>
      </div>

      <Card className="flex-1 flex flex-col min-h-0 mt-2 overflow-hidden">
        <div ref={scrollRef} className="flex-1 overflow-y-auto p-5 space-y-4">
          {messages.length === 0 && (
            <div className="h-full flex flex-col items-center justify-center text-center">
              <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-brand-500 to-violet-500 text-white grid place-items-center text-2xl mb-3">
                अ
              </div>
              <p className="text-slate-500 font-medium">{t("student.chat.readyTutor")}</p>
              <p className="text-sm text-slate-400 mb-4">{t("student.chat.citedAnswers")}</p>
              <div className="flex flex-wrap gap-2 justify-center max-w-md">
                {SUGGESTIONS.map((s) => (
                  <button
                    key={s}
                    onClick={() => send(s)}
                    className="text-sm bg-slate-100 hover:bg-brand-100 hover:text-brand-700 text-slate-600 rounded-full px-3.5 py-1.5 transition"
                  >
                    {s}
                  </button>
                ))}
              </div>
            </div>
          )}

          {messages.map((m, i) => (
            <div key={i} className={`flex gap-2.5 ${m.role === "user" ? "justify-end" : "justify-start"}`}>
              {m.role === "assistant" && (
                <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-brand-500 to-violet-500 text-white grid place-items-center text-sm shrink-0">
                  अ
                </div>
              )}
              <div className={`max-w-[78%] ${m.role === "user" ? "items-end" : "items-start"} flex flex-col`}>
                <div
                  className={`px-4 py-2.5 rounded-2xl text-sm whitespace-pre-wrap leading-relaxed ${
                    m.role === "user"
                      ? "bg-brand-600 text-white rounded-br-md"
                      : "bg-slate-100 text-slate-800 rounded-bl-md"
                  }`}
                >
                  {m.content ? (
                    m.content
                  ) : streaming && i === messages.length - 1 ? (
                    <span className="inline-flex gap-1 py-1">
                      <Dot /> <Dot delay="150ms" /> <Dot delay="300ms" />
                    </span>
                  ) : (
                    ""
                  )}
                </div>
                {m.role === "assistant" && m.citations && <CitationList citations={m.citations} />}
              </div>
            </div>
          ))}
        </div>

        <form
          className="border-t border-slate-100 p-3 flex items-center gap-2 bg-white"
          onSubmit={(e) => {
            e.preventDefault();
            send(input);
          }}
        >
          <VoiceInputButton onTranscript={(t) => send(t)} />
          <input
            className="flex-1 px-4 py-2.5 rounded-xl border border-slate-300 text-sm focus:outline-none focus:ring-2 focus:ring-brand-200 focus:border-brand-400 transition"
            placeholder={t("student.chat.inputPlaceholder")}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            disabled={streaming}
          />
          <button
            type="submit"
            disabled={streaming || !input.trim()}
            className="w-11 h-11 rounded-xl bg-brand-600 hover:bg-brand-700 text-white grid place-items-center transition disabled:opacity-40 shrink-0"
            title={t("student.chat.send")}
          >
            ➤
          </button>
        </form>
      </Card>
    </div>
  );
}

function Dot({ delay = "0ms" }: { delay?: string }) {
  return (
    <span
      className="w-1.5 h-1.5 rounded-full bg-slate-400 animate-bounce"
      style={{ animationDelay: delay }}
    />
  );
}
