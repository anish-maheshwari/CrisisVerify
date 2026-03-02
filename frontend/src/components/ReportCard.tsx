"use client";

import React, { useState } from "react";
import { ClaimResult, Evidence, ScoreBreakdown, Verdict } from "@/types/analysis";

interface ReportCardProps {
    claimResult: ClaimResult;
    index: number;
}

const VERDICT_COLORS: Record<Verdict, string> = {
    Verified: "#22c55e",
    Developing: "#f59e0b",
    "Likely False": "#ef4444",
};

function SourceBadge({ weight }: { weight: number }) {
    const { label, color } =
        weight >= 0.85 ? { label: "Gov/Academic", color: "#22c55e" } :
            weight >= 0.75 ? { label: "Trusted Media", color: "#22c55e" } :
                weight >= 0.50 ? { label: "NGO", color: "#f59e0b" } :
                    { label: "Unknown", color: "#ef4444" };
    return (
        <span className="source-badge" style={{ color, borderColor: `${color}44` }}>
            {label} ({(weight * 100).toFixed(0)}%)
        </span>
    );
}

function StanceSummaryBanner({ breakdown }: { breakdown: ScoreBreakdown }) {
    const { support_ratio, refute_ratio, stance_summary } = breakdown;

    let icon = "◈";
    let color = "#94a3b8";    // neutral gray
    let bgColor = "rgba(148, 163, 184, 0.06)";
    let borderColor = "rgba(148, 163, 184, 0.2)";

    if (refute_ratio >= 0.6) {
        icon = "✕"; color = "#ef4444";
        bgColor = "rgba(239, 68, 68, 0.06)"; borderColor = "rgba(239, 68, 68, 0.25)";
    } else if (support_ratio >= 0.6) {
        icon = "✓"; color = "#22c55e";
        bgColor = "rgba(34, 197, 94, 0.06)"; borderColor = "rgba(34, 197, 94, 0.25)";
    } else if (refute_ratio > 0 || support_ratio > 0) {
        icon = "⚡"; color = "#f59e0b";
        bgColor = "rgba(245, 158, 11, 0.06)"; borderColor = "rgba(245, 158, 11, 0.25)";
    }

    const supportPct = Math.round(support_ratio * 100);
    const refutePct = Math.round(refute_ratio * 100);

    return (
        <div className="stance-banner" style={{ background: bgColor, borderColor }}>
            <span className="stance-icon" style={{ color }}>{icon}</span>
            <div className="stance-content">
                <span className="stance-summary" style={{ color }}>{stance_summary}</span>
                {(supportPct > 0 || refutePct > 0) && (
                    <div className="stance-ratios">
                        {supportPct > 0 && (
                            <span className="stance-ratio" style={{ color: "#22c55e" }}>
                                ✓ {supportPct}% support
                            </span>
                        )}
                        {refutePct > 0 && (
                            <span className="stance-ratio" style={{ color: "#ef4444" }}>
                                ✕ {refutePct}% refute
                            </span>
                        )}
                    </div>
                )}
            </div>
        </div>
    );
}

function EvidenceQualitySummary({ evidence }: { evidence: Evidence[] }) {
    const high = evidence.filter((e) => e.credibility_weight >= 0.75).length;
    const low = evidence.length - high;
    const color = high >= evidence.length / 2 ? "#22c55e" : "#f59e0b";
    return (
        <div className="evidence-quality-summary" style={{ borderColor: `${color}33` }}>
            <span className="eq-icon" style={{ color }}>◈</span>
            <span className="eq-text">
                <strong>{evidence.length}</strong> source{evidence.length !== 1 ? "s" : ""} retrieved:{" "}
                <span style={{ color: "#22c55e" }}>{high} high-credibility</span>
                {low > 0 && (
                    <>
                        {", "}
                        <span style={{ color: "#ef4444" }}>{low} low-credibility</span>
                    </>
                )}
            </span>
        </div>
    );
}

interface ComponentBarProps {
    label: string;
    rawScore: number;
    contribution: number;
    maxContribution: number;
    weight: string;
    color: string;
}

function ComponentBar({ label, rawScore, contribution, maxContribution, weight, color }: ComponentBarProps) {
    const fillPct = Math.round((contribution / maxContribution) * 100);
    return (
        <div className="score-component-row">
            <div className="sc-header">
                <span className="sc-label">{label}</span>
                <span className="sc-weight" style={{ color: "#94a3b8" }}>weight {weight}</span>
                <span className="sc-pts" style={{ color }}>{contribution.toFixed(1)} pts</span>
            </div>
            <div className="sc-bar-track">
                <div className="sc-bar-fill" style={{ width: `${fillPct}%`, background: color }} />
            </div>
            <div className="sc-raw" style={{ color: "#64748b" }}>raw: {rawScore.toFixed(0)}/100</div>
        </div>
    );
}

function ScoreBreakdownPanel({ breakdown }: { breakdown: ScoreBreakdown }) {
    const baseScore =
        breakdown.weighted_source_component +
        breakdown.stance_component +
        breakdown.relevance_component +
        breakdown.recency_component;

    return (
        <div className="score-breakdown-panel">
            <div className="sb-title">Score Breakdown</div>
            <div className="sb-formula">
                BaseScore = (Source × 0.40) + (Stance × 0.35) + (Relevance × 0.15) + (Recency × 0.10)
            </div>
            <div className="sc-components">
                <ComponentBar label="Source Credibility" rawScore={breakdown.weighted_source_score} contribution={breakdown.weighted_source_component} maxContribution={40} weight="40%" color="#6366f1" />
                <ComponentBar label="Stance Score" rawScore={breakdown.stance_score} contribution={breakdown.stance_component} maxContribution={35} weight="35%" color={breakdown.refute_ratio >= 0.6 ? "#ef4444" : breakdown.support_ratio >= 0.6 ? "#22c55e" : "#f59e0b"} />
                <ComponentBar label="Relevance" rawScore={breakdown.relevance_score} contribution={breakdown.relevance_component} maxContribution={15} weight="15%" color="#f59e0b" />
                <ComponentBar label="Recency" rawScore={breakdown.recency_score} contribution={breakdown.recency_component} maxContribution={10} weight="10%" color="#06b6d4" />
            </div>
            <div className="sb-totals">
                <span className="sb-base">Base Score: <strong>{baseScore.toFixed(1)}</strong></span>
                {breakdown.crisis_modifier < 1.0 && (
                    <span className="sb-crisis">× {breakdown.crisis_modifier} → <strong>{breakdown.final_score.toFixed(1)}</strong></span>
                )}
            </div>
        </div>
    );
}

function EvidenceItem({ ev }: { ev: Evidence }) {
    return (
        <div className="evidence-item">
            <div className="evidence-header">
                <a href={ev.url} target="_blank" rel="noopener noreferrer" className="evidence-source">
                    {ev.source_name}
                </a>
                <SourceBadge weight={ev.credibility_weight} />
                {ev.published_date && <span className="evidence-date">{ev.published_date}</span>}
            </div>
            <p className="evidence-snippet">"{ev.snippet}"</p>
        </div>
    );
}

export function ReportCard({ claimResult, index }: ReportCardProps) {
    const [expanded, setExpanded] = useState(false);
    const { claim, score, evidence } = claimResult;
    const color = VERDICT_COLORS[score.verdict];

    return (
        <div className="report-card" style={{ borderLeftColor: color }}>
            <div
                className="report-card-header"
                onClick={() => setExpanded((v) => !v)}
                role="button"
                aria-expanded={expanded}
                tabIndex={0}
                onKeyDown={(e) => e.key === "Enter" && setExpanded((v) => !v)}
            >
                <div className="claim-number" style={{ color }}>#{index + 1}</div>
                <div className="claim-text">{claim}</div>
                <div className="claim-verdict-badge" style={{ background: `${color}22`, color, border: `1px solid ${color}55` }}>
                    {score.verdict}
                </div>
                <div className="claim-score-chip" style={{ color }}>{score.claim_score.toFixed(0)}</div>
                <div className="expand-icon">{expanded ? "▲" : "▼"}</div>
            </div>

            {expanded && (
                <div className="report-card-body">
                    {/* Stance summary — most prominent element */}
                    {score.breakdown && (
                        <StanceSummaryBanner breakdown={score.breakdown} />
                    )}

                    {/* Evidence quality */}
                    <EvidenceQualitySummary evidence={evidence} />

                    {/* Score breakdown bars */}
                    {score.breakdown && (
                        <ScoreBreakdownPanel breakdown={score.breakdown} />
                    )}

                    {/* Full reasoning lines */}
                    <div className="reasoning-box">
                        <div className="reasoning-label">Detailed Reasoning</div>
                        {score.reasoning.split(" | ").map((line, i) => (
                            <div key={i} className="reasoning-line">{line}</div>
                        ))}
                    </div>

                    {/* Evidence list */}
                    <div className="evidence-section">
                        <h4 className="evidence-title">Evidence Sources ({evidence.length})</h4>
                        {evidence.map((ev, i) => <EvidenceItem key={i} ev={ev} />)}
                    </div>
                </div>
            )}
        </div>
    );
}
