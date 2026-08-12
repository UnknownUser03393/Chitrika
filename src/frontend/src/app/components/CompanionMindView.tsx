import { useCallback, useEffect, useMemo, useState } from "react";
import { Brain, Database, Heart, Pin, PinOff, Plus, RefreshCw, Trash2, Users, X } from "lucide-react";
import { toast } from "sonner";
import type { Character, EmotionState, Memory, RelationshipState } from "../services/api";
import {
  createMemory,
  deleteMemory,
  fetchEmotion,
  fetchMemories,
  fetchRelationship,
  updateMemory,
} from "../services/api";

const EMOTION_LABELS: Record<string, string> = {
  joy: "Joy",
  sadness: "Sadness",
  anger: "Anger",
  fear: "Fear",
  trust: "Trust",
  anticipation: "Anticipation",
  surprise: "Surprise",
  disgust: "Disgust",
};

export function CompanionMindView({ character, onClose }: { character: Character; onClose: () => void }) {
  const [emotion, setEmotion] = useState<EmotionState | null>(null);
  const [memories, setMemories] = useState<Memory[]>([]);
  const [relationship, setRelationship] = useState<RelationshipState | null>(null);
  const [loading, setLoading] = useState(true);
  const [includeForgotten, setIncludeForgotten] = useState(false);
  const [draft, setDraft] = useState("");
  const [adding, setAdding] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [nextEmotion, nextMemories, nextRelationship] = await Promise.all([
        fetchEmotion(character.id),
        fetchMemories(character.id, includeForgotten),
        fetchRelationship(character.id),
      ]);
      setEmotion(nextEmotion);
      setMemories(nextMemories);
      setRelationship(nextRelationship);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Failed to load companion state");
    } finally {
      setLoading(false);
    }
  }, [character.id, includeForgotten]);

  useEffect(() => { load(); }, [load]);

  const groups = useMemo(() => ({
    long_term: memories.filter((memory) => memory.memory_type === "long_term"),
    episodic: memories.filter((memory) => memory.memory_type === "episodic"),
    short_term: memories.filter((memory) => memory.memory_type === "short_term"),
  }), [memories]);

  const addMemory = async () => {
    const content = draft.trim();
    if (!content) return;
    setAdding(true);
    try {
      await createMemory(character.id, {
        memory_type: "long_term",
        content,
        importance: 0.8,
        is_pinned: true,
      });
      setDraft("");
      await load();
      toast.success("Memory added");
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Failed to add memory");
    } finally {
      setAdding(false);
    }
  };

  const patchMemory = async (memory: Memory, updates: Parameters<typeof updateMemory>[1]) => {
    try {
      const updated = await updateMemory(memory.id, updates);
      setMemories((current) => current.map((item) => item.id === updated.id ? updated : item));
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Failed to update memory");
    }
  };

  const removeMemory = async (memory: Memory) => {
    try {
      await deleteMemory(memory.id);
      setMemories((current) => current.filter((item) => item.id !== memory.id));
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Failed to delete memory");
    }
  };

  return (
    <div className="flex h-full w-full flex-col bg-[var(--app-bg)]">
      <header className="flex min-h-16 items-center gap-3 border-b border-[var(--app-border)] px-6">
        <div className="flex h-9 w-9 items-center justify-center rounded-full text-white" style={{ background: character.color }}>
          {character.initials || character.display_name.slice(0, 1)}
        </div>
        <div className="min-w-0 flex-1">
          <h1 className="truncate text-base font-semibold text-[var(--app-text)]">{character.display_name} · Mind & Memory</h1>
          <p className="text-xs text-[var(--app-muted)]">Live state used to assemble every reply</p>
        </div>
        <button onClick={load} className="rounded-lg p-2 text-[var(--app-muted)] hover:bg-white/5 hover:text-[var(--app-text)]" aria-label="Refresh">
          <RefreshCw size={17} className={loading ? "animate-spin" : ""} />
        </button>
        <button onClick={onClose} className="rounded-lg p-2 text-[var(--app-muted)] hover:bg-white/5 hover:text-[var(--app-text)]" aria-label="Close">
          <X size={18} />
        </button>
      </header>

      <div className="flex-1 overflow-y-auto p-6">
        <div className="mx-auto grid max-w-5xl gap-5 lg:grid-cols-[minmax(260px,0.8fr)_minmax(360px,1.2fr)]">
          <section className="rounded-2xl border border-[var(--app-border)] bg-[var(--app-panel)] p-5">
            <div className="mb-4 flex items-center gap-2"><Users size={17} className="text-violet-400" /><h2 className="font-semibold">Relationship</h2></div>
            {relationship ? (
              <div className="mb-6">
                <div className="mb-3 rounded-xl bg-white/[0.035] p-3">
                  <div className="text-lg font-semibold capitalize">{relationship.stage}</div>
                  <div className="mt-1 text-xs text-[var(--app-muted)]">{relationship.interaction_count} conversations · {relationship.positive_interaction_count} positive · {relationship.conflict_count} conflicts</div>
                </div>
                <div className="space-y-2.5">
                  {([
                    ["Affinity", relationship.affinity],
                    ["Familiarity", relationship.familiarity],
                    ["Relationship trust", relationship.trust],
                  ] as const).map(([label, value]) => (
                    <div key={label}>
                      <div className="mb-1 flex justify-between text-xs"><span>{label}</span><span className="text-[var(--app-muted)]">{Math.round(value * 100)}%</span></div>
                      <div className="h-1.5 overflow-hidden rounded-full bg-white/10"><div className="h-full rounded-full bg-violet-400" style={{ width: `${value * 100}%` }} /></div>
                    </div>
                  ))}
                </div>
              </div>
            ) : null}

            <div className="mb-4 flex items-center gap-2 border-t border-[var(--app-border)] pt-5"><Heart size={17} className="text-rose-400" /><h2 className="font-semibold">Emotional state</h2></div>
            {emotion ? (
              <>
                <div className="mb-5 rounded-xl bg-white/[0.035] p-3">
                  <div className="text-lg font-semibold capitalize">{emotion.mood}</div>
                  <div className="mt-1 text-xs text-[var(--app-muted)]">Dominant: {emotion.dominant} · Loneliness {Math.round(emotion.loneliness * 100)}%</div>
                </div>
                <div className="space-y-3">
                  {Object.entries(emotion.emotions).map(([name, value]) => (
                    <div key={name}>
                      <div className="mb-1 flex justify-between text-xs"><span>{EMOTION_LABELS[name] || name}</span><span className="text-[var(--app-muted)]">{value.toFixed(2)}</span></div>
                      <div className="h-1.5 overflow-hidden rounded-full bg-white/10"><div className="h-full rounded-full bg-[var(--app-accent)]" style={{ width: `${Math.max(0, Math.abs(value)) * 100}%`, opacity: value < 0 ? 0.45 : 1 }} /></div>
                    </div>
                  ))}
                </div>
              </>
            ) : <p className="text-sm text-[var(--app-muted)]">No emotion state available.</p>}
          </section>

          <section className="rounded-2xl border border-[var(--app-border)] bg-[var(--app-panel)] p-5">
            <div className="mb-4 flex items-center gap-2"><Database size={17} className="text-amber-400" /><h2 className="font-semibold">Memory</h2><span className="ml-auto text-xs text-[var(--app-muted)]">{memories.length} items</span></div>
            <div className="mb-4 flex gap-2">
              <input value={draft} onChange={(event) => setDraft(event.target.value)} onKeyDown={(event) => { if (event.key === "Enter") addMemory(); }} placeholder="Add a fact this character should remember…" className="min-w-0 flex-1 rounded-xl border border-[var(--app-border)] bg-transparent px-3 py-2 text-sm outline-none focus:border-[var(--app-accent)]" />
              <button onClick={addMemory} disabled={adding || !draft.trim()} className="rounded-xl bg-[var(--app-accent)] px-3 text-white disabled:opacity-40" aria-label="Add memory"><Plus size={17} /></button>
            </div>
            <label className="mb-4 flex cursor-pointer items-center gap-2 text-xs text-[var(--app-muted)]"><input type="checkbox" checked={includeForgotten} onChange={(event) => setIncludeForgotten(event.target.checked)} />Show forgotten memories</label>
            <div className="space-y-5">
              {(["long_term", "episodic", "short_term"] as const).map((type) => groups[type].length > 0 && (
                <div key={type}>
                  <h3 className="mb-2 text-[11px] font-bold uppercase tracking-wider text-[var(--app-muted)]">{type.replace("_", " ")}</h3>
                  <div className="space-y-2">{groups[type].map((memory) => (
                    <div key={memory.id} className={`group rounded-xl bg-white/[0.035] p-3 ${memory.is_forgotten ? "opacity-45" : ""}`}>
                      <p className="text-sm leading-relaxed text-[var(--app-text)]">{memory.content}</p>
                      <div className="mt-2 flex items-center gap-2 text-[11px] text-[var(--app-muted)]">
                        <span>importance {Math.round(memory.importance * 100)}%</span><span>·</span><span>used {memory.access_count}×</span>
                        <div className="ml-auto flex gap-1">
                          <button onClick={() => patchMemory(memory, { is_pinned: !memory.is_pinned })} className="rounded p-1 hover:bg-white/10" title={memory.is_pinned ? "Unpin" : "Pin"}>{memory.is_pinned ? <PinOff size={14} /> : <Pin size={14} />}</button>
                          <button onClick={() => patchMemory(memory, { is_forgotten: !memory.is_forgotten })} className="rounded p-1 hover:bg-white/10" title={memory.is_forgotten ? "Restore" : "Forget"}><Brain size={14} /></button>
                          <button onClick={() => removeMemory(memory)} className="rounded p-1 hover:bg-red-500/10 hover:text-red-400" title="Delete permanently"><Trash2 size={14} /></button>
                        </div>
                      </div>
                    </div>
                  ))}</div>
                </div>
              ))}
              {!loading && memories.length === 0 && <div className="py-10 text-center text-sm text-[var(--app-muted)]">No memories yet. They will form as you talk.</div>}
            </div>
          </section>
        </div>
      </div>
    </div>
  );
}
