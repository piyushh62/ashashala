import { useTranslation } from "react-i18next";
import { Icon } from "../ui";
import { useVoice } from "../../stores/voice";

// Speaks text via the browser SpeechSynthesis using the user's voice settings.
// Server fallback (NVIDIA TTS) is available via studentApi.ttsUrl if unsupported.
export function speak(text: string, langHint = "en") {
  const synth = window.speechSynthesis;
  if (!synth) return false;
  const { rate, pitch, voiceURI } = useVoice.getState();
  synth.cancel();
  const u = new SpeechSynthesisUtterance(text);
  u.rate = rate;
  u.pitch = pitch;
  u.lang = langHint === "en" ? "en-IN" : `${langHint}-IN`;
  if (voiceURI) {
    const v = synth.getVoices().find((x) => x.voiceURI === voiceURI);
    if (v) u.voice = v;
  }
  synth.speak(u);
  return true;
}

export function TTSToggle() {
  const { t } = useTranslation();
  const { ttsEnabled, toggleTts } = useVoice();
  return (
    <button
      onClick={toggleTts}
      className={`inline-flex items-center gap-1.5 text-xs px-2 py-1 rounded-full ${
        ttsEnabled ? "bg-brand-100 text-brand-700" : "bg-slate-100 text-slate-500"
      }`}
      title={t("student.voice.speakAloud")}
    >
      <Icon name={ttsEnabled ? "volume" : "volumeOff"} className="w-3.5 h-3.5" />
      {ttsEnabled ? t("student.voice.voiceOn") : t("student.voice.voiceOff")}
    </button>
  );
}
