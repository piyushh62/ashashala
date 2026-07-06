import { beforeEach, describe, expect, it } from "vitest";
import { useVoice } from "./voice";

describe("voice store", () => {
  beforeEach(() => {
    localStorage.clear();
    useVoice.setState({ rate: 1, pitch: 1, voiceURI: null, ttsEnabled: false });
  });

  it("toggles ttsEnabled and persists it", () => {
    expect(useVoice.getState().ttsEnabled).toBe(false);
    useVoice.getState().toggleTts();
    expect(useVoice.getState().ttsEnabled).toBe(true);

    const persisted = JSON.parse(localStorage.getItem("ashashala_voice") || "{}");
    expect(persisted.ttsEnabled).toBe(true);
  });

  it("persists rate/pitch/voiceURI changes independently", () => {
    useVoice.getState().setRate(1.5);
    useVoice.getState().setPitch(0.8);
    useVoice.getState().setVoiceURI("Google UK English Female");

    expect(useVoice.getState()).toMatchObject({
      rate: 1.5,
      pitch: 0.8,
      voiceURI: "Google UK English Female",
    });
    const persisted = JSON.parse(localStorage.getItem("ashashala_voice") || "{}");
    expect(persisted).toMatchObject({ rate: 1.5, pitch: 0.8, voiceURI: "Google UK English Female" });
  });
});
