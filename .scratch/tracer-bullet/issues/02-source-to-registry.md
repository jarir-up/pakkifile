# 02: Official source to cited registry entries

**What to build:** the cited excerpt of the study visa page becomes three typed, cited requirements in a validated YAML registry entry for German Embassy Islamabad × study visa (D) × self-funded freelancer, with the source's normalised-text checksum. Includes the fetcher, tested against a local server.

**Blocked by:** None (can start immediately). Needs ADR-0042.

**Status:** done

- [x] Extraction precision and recall against the hand-labelled checklist are both 1.0
- [x] An entry missing any R-21 citation field fails validation
- [x] Checksum ignores whitespace-only changes and changes when the text changes
