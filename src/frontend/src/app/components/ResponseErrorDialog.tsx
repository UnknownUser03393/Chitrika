import { AlertTriangle, Copy } from "lucide-react";

import type { StreamErrorInfo } from "../services/api";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "./ui/dialog";

interface Props {
  error: StreamErrorInfo | null;
  onClose: () => void;
}

export function ResponseErrorDialog({ error, onClose }: Props) {
  return (
    <Dialog open={error !== null} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="border-[var(--app-border)] bg-[var(--app-panel)] text-[var(--app-text)] sm:max-w-lg">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <AlertTriangle size={19} className="text-amber-500" />
            Response Error
          </DialogTitle>
          <DialogDescription className="text-[var(--app-muted)]">
            {error?.message}
          </DialogDescription>
        </DialogHeader>
        <div>
          <div className="mb-2 text-xs font-semibold uppercase tracking-wide text-[var(--app-muted)]">
            Details
          </div>
          <pre className="max-h-52 overflow-auto whitespace-pre-wrap break-words rounded-lg border border-[var(--app-border)] bg-[var(--app-bg)] p-3 text-xs text-[var(--app-text)]">
            {error?.details}
          </pre>
        </div>
        <DialogFooter>
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg border border-[var(--app-border)] px-4 py-2 text-sm"
          >
            Close
          </button>
          <button
            type="button"
            onClick={() => void navigator.clipboard.writeText(error?.details || "")}
            className="inline-flex items-center justify-center gap-2 rounded-lg bg-[var(--app-accent)] px-4 py-2 text-sm text-white"
          >
            <Copy size={14} /> Copy Details
          </button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
