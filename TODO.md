# TODO.md

## Bugs

- Evaluators should EXCLUDE annotations from testing accounts (Done)

## Features

- User Guide
- Should the Image Preview feature be a pop-up window of Dashboard? (Answer: No)
- Block mobile access? (Done)
- Split up the Preview feature out of the Label file? So there are /label /preview /reader
- Colorful touch-ups to the boxes in Dashboard (Yes)
- Refine admin features:

- Off-style checkboxes in Admin panel: Show Inactive in Accounts Panel; Testing Account checkbox when admin makes new account (Done)

- All toasts should respect dark/light mode (Done)

- Timing count of each image set annotation
- Update Pop-Up
- Telemetry? (If doctors use which kind of tooltip, timing count for each annotation of image set, how many images do they see?, ...)
- Keyboard Shortcut highlights in each button/important buttons, simple highlight in some, in tooltips in some (in idea development)
- Shift + ESC to return to Dashboard (Of course still with warnings, as if you press the button) (Done)
- Shift + Del to Reset All Annotations(this include in the Keyboard Shortcuts Panel) (The pop up would have answered via keyboard with Y(Yes, Delete) or N (No, Cancel), so the button rename from Cancel to No, Cancel) (Done)
- Tab on About box to toggle Developer Information (this is hidden in Keyboard Shortcuts Panel) (Done)
- Arrow-based keyboard navigation for the Management Board. You move up, down. Left/Right to switch left/right table cursor. (Done)
- Press W would jump you into WL number input, press Tab if you are in WL to jump to WW input, press Tab from WW to jump back to WL, in either, press Enter to apply new windowing while Shift+W resets the windowing (Done)
- Shift + Tab cycles through Image Set Evaluation tabs (Done)
- Press J to go to Jump to Image number input while Shift+J go to Jump to Image Set Number input (Done)
Dashboard:
- Make the table fit the page (Done)
- Ctrl A to tick all image sets (Done)
- Asking to Annotate/Preview/Read >= 50 image sets prompt a box warning the amount and tell that it can affect system stability. Two options. Yes. Proceed (Y, Blue) No. Cancel (N, No Color), Esc assumes No (Done)
- Tabs to switch tabs: Image Sets, Drafts, History (Done)
- Drafts: Del/Shift+D to delete drafts (Done)
- Shrink the consecutive image set ID chosen (Done)
- Vim-like Visual Mode for table. Toggle with V and a Visual tag below the table
Labeling:
- Low Quality Toggle change from Q to Shift + Q (Done)
- After choosing Anomaly & Irrelevant (either by mouse or keyboard), jumps to the set-level notes (Done)
- Rapid Zone Score Mode: When the set is Ischemic Assessable, zone is Basal / Corona already (Scenario 1) OR switching between zones BY KEYBOARD (Scenario 2), activate Rapid Zone Score Mode.
+ Prepare before implement this mode: Change Basal/Corona/None region to Shift + B/C/N to prevent mistyping
+ Scenario 1 uses a dedicated key (Z / Tab? which one?)
+ Scenario 2: currently, pressing a zone while it is that zone itself (B while in Basal) would reset the zone annotation. I like that idea. So choosing a zone via keyboard also activate RZSM
+ Currently, the zone scoring is a grid with columns of Left/Right, rows of zones, we make a hireachy like reading: top left cell, top right cell, then left lower cell,...so on (remember this order)
+ RZSM when activated would point a cursor highlight to the cell of : (I have two options here: One is just put on top left, no matter the state OR the cell of priority NOT graded yet, by hireachy order (higher row, lefter column))
+ In a highlighted cell, press (i have two options here: 0 means Damaged, 1 mean Not Damanged, 2 means Not Visible; or 1 means Damaged, 2 mean not Damaged, 3 means Not Visible, the former respects ASPECTS but the latter feels keys are closer together, or third option, some combinations of 3 nearby keys, no matter what it is) it would jump to the next cell of the hireachy, so on so on...
+ RZSM is exit when user press the activation key or ESC, changing image set usability (if perform changing, jump to Image and Jump to Set, should RZSM keep ON if the jumped image/set is RZSM-capabled?)
+ The cursor of RZSM can move anywhere in the grid via keyboard arrows and also Shift + Up/Down to move to same column, highest/lowest row. (but should we block overflowing keys or they cycle in the same row/column or let them overflow the hireachy?)
+ This is for single-cell annotation, they can expand to multi-cell, Vim motions,...but try to think single-cell first


- Visual Mode in cells should also include how many image sets are done, how many image are in draft, how many are pending
- Shift + N focuses on Image Set Notes
## Hard Features

- Vietnamese Support
