"use client";

import { SecurityPolicy } from "@/types";

interface Props {
  policy: SecurityPolicy;
  onUpdate: (patch: Partial<SecurityPolicy>) => void;
}

function sliderTrack(val: number, min: number, max: number, activeColor: string): string {
  const span = max - min;
  const pct = span <= 0 ? 100 : Math.max(0, Math.min(100, ((val - min) / span) * 100));
  return `linear-gradient(to right, ${activeColor} 0%, ${activeColor} ${pct}%, var(--border-subtle, #273244) ${pct}%, var(--border-subtle, #273244) 100%)`;
}

export function PolicyThresholdBars({ policy, onUpdate }: Props) {
  const minScore = policy.min_security_score ?? 80;
  const warnScore = Math.max(minScore, policy.warn_security_score ?? Math.min(100, minScore + 10));
  const conf = policy.confidence_threshold ?? 70;
  const blockCvss = ((100 - minScore) / 10).toFixed(1);
  const warnCvss = ((100 - warnScore) / 10).toFixed(1);

  const blockWidth = minScore;
  const warnWidth = Math.max(0, warnScore - minScore);
  const passWidth = Math.max(0, 100 - warnScore);

  return (
    <div className="pt-4 mt-4 border-t space-y" style={{ borderColor: "var(--border-subtle)" }}>
      {/* Dynamic Multi-Zone Gate Spectrum Bar */}
      <div>
        <div className="flex-between mb-1.5 text-xs">
          <span className="font-semibold text-main">Dynamic Security Gate Spectrum (0–100 Score)</span>
          <span className="font-mono text-[11px] text-muted">
            BLOCK &lt; {minScore} &middot; WARN {minScore}–{warnScore} &middot; PASS &ge; {warnScore}
          </span>
        </div>
        <div
          className="w-full flex overflow-hidden rounded-full border"
          style={{ height: "12px", borderColor: "var(--border-subtle)" }}
        >
          <div
            style={{ width: `${blockWidth}%`, backgroundColor: "var(--crit-color)", transition: "width 120ms ease" }}
            title={`BLOCKED zone: 0 to ${minScore - 1}`}
          />
          <div
            style={{ width: `${warnWidth}%`, backgroundColor: "var(--med-color)", transition: "width 120ms ease" }}
            title={`WARNING zone: ${minScore} to ${warnScore - 1}`}
          />
          <div
            style={{ width: `${passWidth}%`, backgroundColor: "var(--pass-color)", transition: "width 120ms ease" }}
            title={`PASSED zone: ${warnScore} to 100`}
          />
        </div>
      </div>

      {/* Sliders */}
      <div className="grid-2 gap-6">
        <div>
          <div className="flex-between mb-1.5 text-xs">
            <label className="font-semibold text-main">Blocking Score Threshold</label>
            <span className="font-mono font-bold" style={{ color: "var(--crit-color)" }}>
              {minScore} / 100 <span className="text-[11px] text-dim">(CVSS &ge; {blockCvss})</span>
            </span>
          </div>
          <input
            type="range"
            min="10"
            max="95"
            step="5"
            value={minScore}
            onChange={(e) => {
              const nextMin = Number(e.target.value);
              onUpdate({
                min_security_score: nextMin,
                warn_security_score: Math.max(nextMin, warnScore),
              });
            }}
            className="policy-range w-full h-2 rounded-lg appearance-none cursor-pointer"
            style={{ background: sliderTrack(minScore, 10, 95, "var(--crit-color)"), accentColor: "var(--crit-color)" }}
          />
          <span className="text-[11px] text-dim block mt-1">
            PRs scoring below {minScore}/100 are automatically marked BLOCKED.
          </span>
        </div>

        <div>
          <div className="flex-between mb-1.5 text-xs">
            <label className="font-semibold text-main">Warning Alert Threshold</label>
            <span className="font-mono font-bold" style={{ color: "var(--med-color)" }}>
              {warnScore} / 100 <span className="text-[11px] text-dim">(CVSS &ge; {warnCvss})</span>
            </span>
          </div>
          <input
            type="range"
            min={minScore}
            max="100"
            step="5"
            value={warnScore}
            onChange={(e) => onUpdate({ warn_security_score: Number(e.target.value) })}
            className="policy-range w-full h-2 rounded-lg appearance-none cursor-pointer"
            style={{ background: sliderTrack(warnScore, minScore, 100, "var(--med-color)"), accentColor: "var(--med-color)" }}
          />
          <span className="text-[11px] text-dim block mt-1">
            PRs between {minScore} and {warnScore} raise a non-blocking WARNING gate.
          </span>
        </div>

        <div>
          <div className="flex-between mb-1.5 text-xs">
            <label className="font-semibold text-main">Minimum AI &amp; Scanner Confidence</label>
            <span className="font-mono font-bold text-accent">{conf}%</span>
          </div>
          <input
            type="range"
            min="60"
            max="99"
            step="1"
            value={conf}
            onChange={(e) => onUpdate({ confidence_threshold: Number(e.target.value) })}
            className="policy-range w-full h-2 rounded-lg appearance-none cursor-pointer"
            style={{ background: sliderTrack(conf, 60, 99, "var(--accent)"), accentColor: "var(--accent)" }}
          />
          <span className="text-[11px] text-dim block mt-1">
            Suppresses findings below {conf}% confidence to prevent noisy blocks.
          </span>
        </div>
      </div>
    </div>
  );
}
