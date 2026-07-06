import { describe, expect, it } from "vitest";
import { hrefFor, labelFor, tsToSeconds } from "./ClickableCitation";
import type { Citation } from "../../types/api";

describe("tsToSeconds", () => {
  it("parses minutes and seconds", () => {
    expect(tsToSeconds("1m24s")).toBe(84);
  });
  it("parses seconds-only timestamps", () => {
    expect(tsToSeconds("45s")).toBe(45);
  });
  it("returns null for missing/unparseable input", () => {
    expect(tsToSeconds(null)).toBeNull();
    expect(tsToSeconds("not-a-timestamp")).toBeNull();
  });
});

describe("hrefFor", () => {
  it("builds a YouTube URL with a ?t= param at the parsed timestamp", () => {
    const c: Citation = {
      source_type: "youtube", url: "https://youtu.be/abc123", timestamp: "1m24s",
      title: "Fractions", filename: null, page: null,
    };
    expect(hrefFor(c)).toBe("https://youtu.be/abc123?t=84");
  });

  it("appends to an existing query string with &", () => {
    const c: Citation = {
      source_type: "youtube", url: "https://youtu.be/abc123?list=xyz", timestamp: "5s",
      title: "Fractions", filename: null, page: null,
    };
    expect(hrefFor(c)).toBe("https://youtu.be/abc123?list=xyz&t=5");
  });

  it("adds a #page= fragment for PDF citations with a page number", () => {
    const c: Citation = {
      source_type: "pdf", url: "https://r2.example.com/notes.pdf", page: 7,
      filename: "notes.pdf", title: null, timestamp: null,
    };
    expect(hrefFor(c)).toBe("https://r2.example.com/notes.pdf#page=7");
  });

  it("returns the bare URL for a generic web citation", () => {
    const c: Citation = {
      source_type: "url", url: "https://en.wikipedia.org/wiki/Fraction",
      filename: null, title: "Fraction", page: null, timestamp: null,
    };
    expect(hrefFor(c)).toBe("https://en.wikipedia.org/wiki/Fraction");
  });

  it("returns null when there is nothing to link to", () => {
    const c: Citation = { source_type: "pdf", url: null, filename: "x.pdf", title: null, page: 1, timestamp: null };
    expect(hrefFor(c)).toBeNull();
  });
});

describe("labelFor", () => {
  it("labels a YouTube citation with title and timestamp", () => {
    const c: Citation = {
      source_type: "youtube", title: "Fractions 101", timestamp: "1m24s",
      url: null, filename: null, page: null,
    };
    expect(labelFor(c)).toBe("▶ Fractions 101 · 1m24s");
  });

  it("labels a PDF citation with filename and page", () => {
    const c: Citation = {
      source_type: "pdf", filename: "notes.pdf", page: 7,
      url: null, title: null, timestamp: null,
    };
    expect(labelFor(c)).toBe("📄 notes.pdf · p.7");
  });
});
