# Design system

Dark, dense, square. Areas are set apart by background tone and 1 px dividers, not boxes. Each colour has exactly one meaning. Approved screens: https://claude.ai/artifact/TUiuZvdvSz2HYGnZLCkRRh (reviewed against Impeccable and gstack's design rules).

| Token | Value | Use |
| --- | --- | --- |
| Ground | `#111315` | App background |
| Rail | `#0D0F11` | Side rails and panels |
| Raised | `#1B1E22` | Selected rows, secondary buttons |
| Sunk | `#0B0D0F` | Inputs |
| Line / line strong | `#24282D` / `#33383F` | Dividers / control borders |
| Text / text 2 / text 3 | `#E9E6DF` / `#A3A7AD` / `#868B92` | Body / secondary / meta (12 px and up only) |
| Amber | `#F0B43C`, tint `#1F1B12`, on-amber `#1C1405` | Your next action, current phase, the one primary button |
| Blue | `#7FB2F0`, tint `#121B26` | Anything Claude did or is doing |
| Green | `#5DBB8A` | Done |
| Red | `#E0626B`, tint `#24151A` | Killed, failed, errors |

## Type
- Schibsted Grotesk 400–700 for everything. JetBrains Mono only for IDs, counts, scores, dates and file paths.
- Sizes: 12 meta, 13 dense tables, 14 interface, 15–16 chat and documents, 20 screen titles, 22–26 page titles.
- Headings in sentence case. No small uppercase labels above headings.

## Shape and layout
- Radius 0 on panels and rows, 2 px on buttons and inputs. Cards only where the card is the thing you interact with.
- Desktop: 232 px rail plus the workspace; side panels 340–420 px.
- Mobile (820 px and below): one pane, bottom bar (Board, Capture, Inbox), touch targets 44 px or more.

## Browser surfaces
Amber selection at 28%, amber caret and focus ring (2 px, 2 px offset), scrollbars in line-strong on ground.

## Motion
150–200 ms state changes and streaming text only. No entrance animations. Respect reduced motion.

## States every screen needs
Loading shapes, empty (teaches the next step), Claude drafting, Claude couldn't answer, sync failed, offline, finishing with unticked items, pasted update.
