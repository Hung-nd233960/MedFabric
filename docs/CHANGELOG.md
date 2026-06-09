# Changelog

## [3.2.4] — 2026-06-10

### Zone Mode — Tab navigation
- **Cell scope**: pressing `Tab` advances the cursor forward (left → right, top → bottom) without scoring, wrapping back to the first cell at the end.
- **Row scope**: `Tab` cycles to the next row (wraps).
- **Col scope**: `Tab` toggles between left and right columns.
- **Vis mode**: `Tab` is intentionally disabled (consumed silently).
- Tab kbd hint added to the Zone Mode guide bar (second row, left side), alongside the arrow key hints, using the same dimmed style as the arrow keys.

### Zone Mode — `0` key behaviour
- In **Cell scope**, pressing `0` now clears the current cell score and advances the cursor (wrapping), matching the predictable forward-movement of `1`/`2`/`3`.
- `Del` / `Backspace` still clear in place (cursor stays), for deliberate undo without moving.
- A `0` kbd hint now appears inline next to the **Not Visible** button on a highlighted cell — only when that cell already has a score, using the same size and style as the `1`/`2`/`3` kbd hints inside the buttons.

### Zone Mode — button layout
- Score button containers switched from `flex flex-wrap` to `flex flex-wrap` with `0` as a natural 4th flex item, giving a consistent 2 + 2 wrap at 100 % zoom without constraining button widths.

### Zone Mode — guide bar reorganisation
- Row 2 right: **Del / Back — clear score** (new hint).
- Row 3 left: Shift+num or `<` `>` to select (moved from row 2 right).
- Row 3 right: V Vis Mode (moved from row 3 left).
- Row 4 left: Ctrl+A to select all / unselect (moved from centred row 4).
- Row 4 right: Esc / Z exit Zone Mode (moved from row 3 right).

### Bug fixes
- **Autosave false trigger**: pressing `Del` / `Backspace` (or `0`) on an already-unscored cell, or pressing `1`/`2`/`3` on a cell that already carries that score, no longer triggers the autosave debounce. Fixed in `labelStore.setScore` by returning the existing state reference when the incoming value equals the current value.

---

## [3.2.3] — prior release
