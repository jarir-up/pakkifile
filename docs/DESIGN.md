# Design — PakkiFile

Feel, tokens, type, and spacing and layout approved by Muhammad Jariruddin, 2026-10-30.

## Feel

Every screen reads like a well-kept case file: calm and document-like, paper-white background, near-black text, one ink-blue accent. Light and dark modes. System font stack, so nothing is downloaded and the app works offline; figures use tabular numerals. Mismatch findings are shown by their M1 to M6 label, never by colour.

The dossier is designed for the reviewing officer, not the applicant, and is ordered the way the authority's checklist is ordered.

## Color tokens
| Token | Light | Dark | Use |
|---|---|---|---|
| `--bg` | `#FBFAF7` | `#161615` | Page background |
| `--fg` | `#1C1B19` | `#EDEBE6` | Body text, form-field borders |
| `--accent` | `#1F4E8C` | `#8DB4E8` | One primary action per screen, links |
| `--danger` | `#B42318` | `#F97066` | Destructive actions and errors only |
| `--line` | `#D9D5CC` | `#3A3834` | Table rules and dividers only; too faint for anything that must be seen to be used |

All text tokens pass WCAG AA against `--bg` (6.3:1 or higher).

## Type
- Family: `system-ui` stack. Every figure uses `font-variant-numeric: tabular-nums`.
- Sizes: 14px table cells and citations, 16px body, 20px section headings, 28px page titles.
- Line height 1.5.

## Spacing and layout
- Spacing steps: 4, 8, 16, 24, 40px.
- Body text at most 72ch wide; tables at most 1100px.
- One breakpoint at 640px; below it, table rows stack as blocks.

## Components
Each component is added here the first time an issue builds it, and the owner approves it in that PR's diff. New UI reuses these before adding new ones.

- **Review table**: rows awaiting review as Date, Description, Amount, Class. Each Class is a menu with the proposed class chosen, or `—` when nothing proposed one. One `Save` button below the table stores every row given a class; a row left on `—` stays.
- **Full-list link**: one paragraph above a checklist table, `Full list: <portal name>` linking to where the authority publishes the rest. Shown only when the entry records one.

## Screen rules
- Every screen has one primary action.
- Labels are the shortest words that work. No taglines, helper text or secondary labels; if a screen needs them, the layout is wrong.
- Requirement type (mandatory, conditional, optional) and confidence are visible on every checklist row.
- Every figure on any screen or export opens its source rows and pages.
- Mismatch findings name their kind (M1 to M6) and the requirement or evidence they concern.
