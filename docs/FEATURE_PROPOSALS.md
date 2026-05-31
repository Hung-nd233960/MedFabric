# MedFabric — Feature Proposals

> Evaluation of proposed features before implementation.
> Status: **Design · not yet built**

---

## 1. Distribute the frontend as an Electron app

### Context

MedFabric is deployed as a Docker Compose stack — PostgreSQL + FastAPI backend + Nginx serving the React SPA — on a hospital intranet. Doctors open the app in a browser. DICOM rendering is server-side (pydicom + Pillow). All persistent state lives in PostgreSQL.

The proposal is to repackage the React frontend as an Electron desktop application so doctors run a native window instead of a browser tab.

### What Electron would and would not change

| | Electron | Current (browser) |
|---|---|---|
| Backend required | Yes (unchanged) | Yes |
| PostgreSQL required | Yes (unchanged) | Yes |
| DICOM server required | Yes (unchanged) | Yes |
| Browser chrome visible | No | Yes |
| OS taskbar integration | Yes | No |
| Install on each workstation | Yes (~200 MB) | No |
| Automatic updates | Needs electron-updater | Redeploy Docker, done |
| IT policy hurdle | App installation approval | None (browser) |

### Analysis

Electron packages only the renderer (the browser). Because DICOM decoding, session management, and the database all run on the server, Electron would still need the Docker stack running on a central machine and would still make HTTP requests to it. The only thing replaced is the browser window.

The gain — a chrome-free window — is real but minor. The costs are substantial for a hospital intranet deployment:

- **IT friction.** Hospitals typically require approval and packaging for desktop software installations. A web app needs nothing.
- **Update burden.** Deploying a fix currently means `docker compose pull && docker compose up`. With Electron, every workstation either needs auto-update infrastructure or manual reinstallation.
- **New tech surface.** Electron adds a main-process / renderer-process model, IPC, `contextBridge`, and Node.js bundling on top of the existing stack — none of which are needed since the app does not use local file system APIs or OS integration.
- **Binary size vs zero.** ~200 MB Electron binary per workstation vs. nothing (browser already installed).

### Verdict: Not recommended

The web + Docker model is the correct architecture for a multi-doctor, server-authoritative, hospital-intranet tool. Electron would add a large maintenance surface for a marginal UX gain.

### Better alternative if an "app-like" window is desired: PWA

A Progressive Web App adds a `manifest.json` and one service-worker registration (~30 lines). Doctors can click "Install" in the browser address bar; the app opens in its own frameless window with no URL bar, appears in the OS taskbar, and receives automatic updates on next open — identical to Electron's window behaviour, with zero installation overhead or build pipeline change.

---

## 2. Apply `beforeunload` to Annotation Mode

### Context

LabelPage already has a navigation guard: `navGuardStore` registers an interceptor on mount that checks for `dirty` state (usability set, low-quality flag, set notes, or any slice with a region or notes filled in). When a doctor clicks a React Router link or the Exit button while dirty, a custom `ConfirmDialog` appears before navigating.

**Gap.** The React Router interceptor only fires for in-app programmatic navigation. It does not fire for:

| Action | Currently protected |
|---|---|
| Exit button / nav link (in-app) | ✅ `navGuardStore` interceptor |
| Browser refresh (F5 / Ctrl+R) | ❌ |
| Close browser tab (Ctrl+W) | ❌ |
| Browser back button | ❌ |
| Typing a new URL in the address bar | ❌ |

Any of these discards the current annotation state silently. On a hospital workstation where doctors are often interrupted, accidental refresh is a realistic risk.

### Solution: `beforeunload` event listener

`window.addEventListener('beforeunload', handler)` fires for all browser-level navigation before the React app has a chance to respond. When the handler calls `event.preventDefault()` and sets `event.returnValue`, the browser shows a native confirmation dialog ("Changes you made may not be saved. Leave site?"). The message text cannot be customised in modern browsers for security reasons — only the prompt itself can be triggered.

**Activation condition** — only active when all of the following hold:
1. Route is LabelPage (component is mounted)
2. `!isReadMode && !isPreviewMode` (annotation mode only)
3. `dirty === true` (same logic as the existing navGuard dirty check)

**Dirty definition** (mirrors the existing interceptor, `LabelPage.tsx:350–354`):
```ts
const dirty =
  st.usability !== null ||
  st.lowQuality ||
  st.setNotes.trim() !== "" ||
  (Object.values(st.slices) as SliceEvalState[]).some(
    (s) => s.region !== "None" || s.notes.trim() !== ""
  );
```

**Sketch implementation** (one `useEffect` in LabelPage, alongside the existing navGuard effect):
```ts
useEffect(() => {
  if (isReadMode || isPreviewMode) return;
  const handler = (e: BeforeUnloadEvent) => {
    const st = useLabelStore.getState();
    const dirty =
      st.usability !== null || st.lowQuality || st.setNotes.trim() !== "" ||
      (Object.values(st.slices) as SliceEvalState[]).some(
        (s) => s.region !== "None" || s.notes.trim() !== ""
      );
    if (dirty) { e.preventDefault(); e.returnValue = ""; }
  };
  window.addEventListener("beforeunload", handler);
  return () => window.removeEventListener("beforeunload", handler);
}, [isReadMode, isPreviewMode]);
```

The cleanup function runs automatically on unmount (normal exit to Dashboard) and whenever `isReadMode` or `isPreviewMode` changes, so the listener is never stale.

### Considerations

- **Draft saves do not clear the guard.** Saving a draft writes to the server but the annotation is not submitted; the guard should stay active. This is the correct behaviour — a saved draft on the server is recoverable, but an in-progress annotation that hasn't even been drafted yet is not.
- **After submission, dirty becomes false** because `reset()` clears all label state, so the handler exits early and the browser navigates without a prompt. No explicit removal needed.
- **Auto-save interplay.** If `autoSaveStatus === "pending"` or `"saving"`, the annotation state is already dirty by definition (there is something to save), so the guard fires automatically.
- **Cannot show a custom message.** Modern browsers (Chrome 51+, Firefox 44+) ignore the string passed to `event.returnValue` and show a generic prompt. The current approach is correct and expected.

### Verdict: Recommended

Low implementation cost (~15 lines), no architectural change, closes a real data-loss gap. Should be added alongside the existing `navGuardStore` effect in LabelPage.
