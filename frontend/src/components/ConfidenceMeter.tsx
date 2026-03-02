"use client";

import React from "react";
import { Verdict } from "@/types/analysis";

interface ConfidenceMeterProps {
    score: number; // 0–100
    verdict: Verdict;
}

/** Human-readable label for each verdict zone */
const ZONE_LABELS = [
    { max: 40, label: "Likely False", color: "#ef4444" },
    { max: 75, label: "Developing", color: "#f59e0b" },
    { max: 100, label: "Verified", color: "#22c55e" },
];

const VERDICT_CONFIG: Record<Verdict, { color: string; glow: string }> = {
    Verified: { color: "#22c55e", glow: "rgba(34,197,94,0.35)" },
    Developing: { color: "#f59e0b", glow: "rgba(245,158,11,0.35)" },
    "Likely False": { color: "#ef4444", glow: "rgba(239,68,68,0.35)" },
};

export function ConfidenceMeter({ score, verdict }: ConfidenceMeterProps) {
    const config = VERDICT_CONFIG[verdict];
    const clamped = Math.max(0, Math.min(100, score));

    return (
        <div className="confidence-meter">
            {/* ── Header ── */}
            <div className="meter-header">
                <span className="meter-label">Overall Confidence</span>
                <span className="meter-score" style={{ color: config.color }}>
                    {clamped.toFixed(1)}
                    <span className="meter-max">/100</span>
                </span>
            </div>

            {/* ── Track + Fill ── */}
            <div
                className="meter-track"
                role="progressbar"
                aria-valuenow={clamped}
                aria-valuemin={0}
                aria-valuemax={100}
                aria-label={`Credibility score: ${clamped.toFixed(1)} out of 100`}
            >
                {/* Zone background segments */}
                <div className="meter-zone zone-false" style={{ width: "40%" }} title="0–40: Likely False" />
                <div className="meter-zone zone-develop" style={{ width: "35%" }} title="40–75: Developing" />
                <div className="meter-zone zone-verify" style={{ width: "25%" }} title="75–100: Verified" />

                {/* Active fill */}
                <div
                    className="meter-fill"
                    style={{
                        width: `${clamped}%`,
                        background: `linear-gradient(90deg, ${config.color}88, ${config.color})`,
                        boxShadow: `0 0 14px ${config.glow}`,
                    }}
                />

                {/* Threshold markers with tooltips */}
                <div className="meter-marker-group" style={{ left: "40%" }}>
                    <div className="meter-marker" />
                    <span className="meter-marker-tooltip">40 — Developing</span>
                </div>
                <div className="meter-marker-group" style={{ left: "75%" }}>
                    <div className="meter-marker" />
                    <span className="meter-marker-tooltip">75 — Verified</span>
                </div>
            </div>

            {/* ── Zone tick labels ── */}
            <div className="meter-zones-row">
                {ZONE_LABELS.map((z) => (
                    <span key={z.label} className="zone-tick-label" style={{ color: z.color }}>
                        {z.label}
                    </span>
                ))}
            </div>

            {/* ── Verdict badge ── */}
            <div
                className="verdict-badge"
                style={{
                    background: config.color,
                    boxShadow: `0 0 16px ${config.glow}`,
                    color: "#000",
                }}
            >
                {verdict}
            </div>
        </div>
    );
}
