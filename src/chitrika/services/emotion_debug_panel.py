"""Tkinter debug panel for live emotion model inference."""

from __future__ import annotations

import logging
import queue
import threading
from dataclasses import dataclass, field
from datetime import datetime
logger = logging.getLogger("chitrika.emotion.debug_panel")

_EVENTS: "queue.Queue[EmotionDebugEvent]" = queue.Queue(maxsize=200)
_THREAD: threading.Thread | None = None
_STOP = threading.Event()


@dataclass
class EmotionDebugEvent:
    source: str
    model_dir: str
    user_text: str
    assistant_text: str
    labels: list[str] = field(default_factory=list)
    probabilities: list[float] = field(default_factory=list)
    deltas: dict[str, float] = field(default_factory=dict)
    metadata: dict[str, object] = field(default_factory=dict)
    error: str | None = None
    created_at: datetime = field(default_factory=datetime.now)


def publish_emotion_debug_event(event: EmotionDebugEvent) -> None:
    """Publish an inference event without blocking the caller."""
    try:
        _EVENTS.put_nowait(event)
    except queue.Full:
        try:
            _EVENTS.get_nowait()
            _EVENTS.put_nowait(event)
        except queue.Empty:
            pass


def start_emotion_debug_panel() -> None:
    """Start the Tkinter panel on a daemon thread."""
    global _THREAD
    if _THREAD is not None and _THREAD.is_alive():
        return
    _STOP.clear()
    _THREAD = threading.Thread(target=_run_panel, name="emotion-debug-panel", daemon=True)
    _THREAD.start()


def stop_emotion_debug_panel() -> None:
    _STOP.set()


def _run_panel() -> None:
    try:
        import tkinter as tk
        from tkinter import ttk
    except Exception:
        logger.exception("Tkinter is not available; emotion debug panel disabled")
        return

    root = tk.Tk()
    root.title("Chitrika Emotion Debug Panel")
    root.geometry("980x720")

    status_var = tk.StringVar(value="Waiting for emotion inference events...")
    source_var = tk.StringVar(value="source: -")
    model_var = tk.StringVar(value="model: -")

    top = ttk.Frame(root, padding=8)
    top.pack(fill=tk.X)
    ttk.Label(top, textvariable=status_var).pack(anchor=tk.W)
    ttk.Label(top, textvariable=source_var).pack(anchor=tk.W)
    ttk.Label(top, textvariable=model_var).pack(anchor=tk.W)

    panes = ttk.PanedWindow(root, orient=tk.VERTICAL)
    panes.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

    text_frame = ttk.Frame(panes)
    panes.add(text_frame, weight=2)
    ttk.Label(text_frame, text="Exchange").pack(anchor=tk.W)
    text_box = tk.Text(text_frame, height=12, wrap=tk.WORD)
    text_box.pack(fill=tk.BOTH, expand=True)

    scores_frame = ttk.Frame(panes)
    panes.add(scores_frame, weight=3)
    ttk.Label(scores_frame, text="Model Scores").pack(anchor=tk.W)
    score_table = ttk.Treeview(scores_frame, columns=("label", "probability", "delta"), show="headings")
    score_table.heading("label", text="Label")
    score_table.heading("probability", text="Probability")
    score_table.heading("delta", text="Mapped Delta")
    score_table.column("label", width=180, anchor=tk.W)
    score_table.column("probability", width=140, anchor=tk.E)
    score_table.column("delta", width=220, anchor=tk.W)
    score_table.pack(fill=tk.BOTH, expand=True)

    delta_frame = ttk.Frame(panes)
    panes.add(delta_frame, weight=1)
    ttk.Label(delta_frame, text="Final Emotion Deltas").pack(anchor=tk.W)
    delta_box = tk.Text(delta_frame, height=6, wrap=tk.WORD)
    delta_box.pack(fill=tk.BOTH, expand=True)

    def update(event: EmotionDebugEvent) -> None:
        status_var.set(f"{event.created_at.strftime('%H:%M:%S')}  {event.source}")
        source_var.set(f"source: {event.source}")
        model_var.set(f"model: {event.model_dir}")

        text_box.configure(state=tk.NORMAL)
        text_box.delete("1.0", tk.END)
        text_box.insert(tk.END, f"USER:\n{event.user_text}\n\nASSISTANT:\n{event.assistant_text}")
        if event.error:
            text_box.insert(tk.END, f"\n\nERROR:\n{event.error}")
        text_box.configure(state=tk.DISABLED)

        score_table.delete(*score_table.get_children())
        delta_by_label = _delta_by_label(event)
        for label, probability in zip(event.labels, event.probabilities):
            score_table.insert(
                "",
                tk.END,
                values=(label, f"{probability:.4f}", delta_by_label.get(label, "")),
            )

        delta_box.configure(state=tk.NORMAL)
        delta_box.delete("1.0", tk.END)
        if event.deltas:
            for key, value in sorted(event.deltas.items()):
                delta_box.insert(tk.END, f"{key}: {value:+.4f}\n")
        else:
            delta_box.insert(tk.END, "No delta emitted")
        delta_box.configure(state=tk.DISABLED)

    def poll() -> None:
        if _STOP.is_set():
            root.destroy()
            return
        try:
            while True:
                update(_EVENTS.get_nowait())
        except queue.Empty:
            pass
        root.after(100, poll)

    root.protocol("WM_DELETE_WINDOW", stop_emotion_debug_panel)
    root.after(100, poll)
    root.mainloop()


def _delta_by_label(event: EmotionDebugEvent) -> dict[str, str]:
    values: dict[str, str] = {}
    metadata = getattr(event, "metadata", None)
    if isinstance(metadata, dict):
        raw = metadata.get("delta_by_label")
        if isinstance(raw, dict):
            for label, delta in raw.items():
                values[str(label)] = str(delta)
    return values

if __name__ == '__main__':
	_run_panel()