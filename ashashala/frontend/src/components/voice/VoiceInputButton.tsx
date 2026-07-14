import { useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { Button, Icon } from "../ui";
import { useToast } from "../ui/Toast";

// Push-to-talk. Prefers the browser Web Speech API; if unsupported, the button
// is hidden (the parent shows a tooltip). No server round-trip in the browser path.
export function VoiceInputButton({
  lang = "en-IN",
  onTranscript,
}: {
  lang?: string;
  onTranscript: (text: string) => void;
}) {
  const { t } = useTranslation();
  const toast = useToast();
  const recRef = useRef<SpeechRecognition | null>(null);
  const [listening, setListening] = useState(false);

  const Supported = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!Supported) {
    return (
      <span
        title={t("student.voice.notSupported")}
        className="text-slate-300 cursor-not-allowed px-3 py-2"
      >
        <Icon name="mic" className="w-4 h-4" />
      </span>
    );
  }

  const start = () => {
    const rec = new Supported();
    rec.lang = lang;
    rec.interimResults = false;
    rec.continuous = false;
    rec.onresult = (e: SpeechRecognitionEvent) => {
      const text = e.results[0]?.[0]?.transcript ?? "";
      if (text) onTranscript(text);
    };
    rec.onerror = () => toast.push(t("student.voice.couldntHear"), "error");
    rec.onend = () => setListening(false);
    recRef.current = rec;
    rec.start();
    setListening(true);
  };

  const stop = () => recRef.current?.stop();

  return (
    <Button
      type="button"
      variant={listening ? "danger" : "ghost"}
      onMouseDown={start}
      onMouseUp={stop}
      onMouseLeave={() => listening && stop()}
      onTouchStart={start}
      onTouchEnd={stop}
      title={t("student.voice.holdToSpeak")}
    >
      <Icon name="mic" className="w-4 h-4" />
      {listening ? t("student.voice.listening") : t("student.voice.hold")}
    </Button>
  );
}
