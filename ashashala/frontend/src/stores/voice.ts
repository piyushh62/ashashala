import { create } from "zustand";

interface VoiceSettings {
  rate: number;
  pitch: number;
  voiceURI: string | null;
  ttsEnabled: boolean;
  setRate: (n: number) => void;
  setPitch: (n: number) => void;
  setVoiceURI: (uri: string | null) => void;
  toggleTts: () => void;
}

const KEY = "ashashala_voice";

function load(): Partial<VoiceSettings> {
  try {
    return JSON.parse(localStorage.getItem(KEY) || "{}");
  } catch {
    return {};
  }
}

function persist(s: VoiceSettings) {
  localStorage.setItem(
    KEY,
    JSON.stringify({ rate: s.rate, pitch: s.pitch, voiceURI: s.voiceURI, ttsEnabled: s.ttsEnabled }),
  );
}

const initial = load();

export const useVoice = create<VoiceSettings>((set, get) => ({
  rate: initial.rate ?? 1,
  pitch: initial.pitch ?? 1,
  voiceURI: initial.voiceURI ?? null,
  ttsEnabled: initial.ttsEnabled ?? false,
  setRate: (rate) => {
    set({ rate });
    persist(get());
  },
  setPitch: (pitch) => {
    set({ pitch });
    persist(get());
  },
  setVoiceURI: (voiceURI) => {
    set({ voiceURI });
    persist(get());
  },
  toggleTts: () => {
    set({ ttsEnabled: !get().ttsEnabled });
    persist(get());
  },
}));
