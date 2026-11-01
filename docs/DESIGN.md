# Offline talk editor design

The release has a newly authored typographic presentation tool, separate from the caller's writing method. It uses system font fallbacks, inline styles and scripts, and no third-party artwork, font payload or remote runtime resource. The visual composition and implementation do not inherit the previous private prototype.

The default artifact contains nine starter slides with stable IDs and unique editable fields. The browser layer handles navigation, notes, overview, plain-text editing, local draft state and complete HTML export. It is not an autonomous content engine, research agent or publisher.

The document remains readable without JavaScript and in print. Narrow layouts prioritize text flow and reachable controls over a shrunken desktop canvas. Typing takes precedence over presentation keyboard shortcuts. Notes and source details remain inspectable and travel with the export, so the author must review their audience and privacy boundary before sharing.

The functional contract is in `contracts/draft-v1.json`; current browser/contract checks are tied to replacement hashes. Old private prototype results are historical evidence only. No design or software check is a claim of better writing or audience outcomes.
