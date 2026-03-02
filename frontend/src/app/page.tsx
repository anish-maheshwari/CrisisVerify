"use client";

import React, { useState } from "react";
import { InputArea } from "@/components/InputArea";
import { ConfidenceMeter } from "@/components/ConfidenceMeter";
import { ReportCard } from "@/components/ReportCard";
import { useAnalysis } from "@/features/analyze/hooks";

export default function HomePage() {
    const [text, setText] = useState("");
    const { result, isLoading, error, analyze, reset } = useAnalysis();

    const handleSubmit = () => analyze(text, false);

    const handleReset = () => {
        setText("");
        reset();
    };

    return (
        <main className="page-container">
            {/* ── Header ───────────────────────────────────── */}
            <header className="site-header">
                <div className="header-logo">
                    <span className="logo-icon">⚡</span>
                    <span className="logo-text">CrisisVerify</span>
                </div>
                <p className="header-tagline">
                    AI-assisted structured claim verification for high-stakes scenarios
                </p>
            </header>

            {/* ── Input ────────────────────────────────────── */}
            <InputArea
                value={text}
                onChange={setText}
                onSubmit={handleSubmit}
                isLoading={isLoading}
            />

            {/* ── Loading ──────────────────────────────────── */}
            {isLoading && (
                <div className="status-panel loading-panel">
                    <div className="pulse-ring" />
                    <div className="loading-steps">
                        <span>Extracting claims</span>
                        <span className="step-sep">→</span>
                        <span>Retrieving evidence</span>
                        <span className="step-sep">→</span>
                        <span>Scoring credibility</span>
                        <span className="step-sep">→</span>
                        <span>Generating report</span>
                    </div>
                </div>
            )}

            {/* ── Error ────────────────────────────────────── */}
            {error && !isLoading && (
                <div className="status-panel error-panel">
                    <span className="error-icon">✕</span>
                    <div>
                        <strong>Analysis Failed</strong>
                        <p>{error}</p>
                    </div>
                    <button className="reset-btn" onClick={handleReset}>Try Again</button>
                </div>
            )}

            {/* ── Results ──────────────────────────────────── */}
            {result && !isLoading && (
                <section className="results-section" aria-label="Analysis Results">

                    {/* Responsible AI Disclaimer Banner */}
                    <div className="ai-disclaimer-banner" role="alert">
                        <span className="ai-banner-icon">🛡</span>
                        <div>
                            <strong>Responsible AI Notice:</strong>{" "}
                            This tool assists claim evaluation. It does not replace professional verification.
                            Always consult authoritative sources before acting on this information.
                        </div>
                    </div>

                    {/* Overall summary */}
                    <div className="results-summary-grid">
                        <ConfidenceMeter
                            score={result.overall_confidence}
                            verdict={result.overall_verdict}
                        />
                        <div className="summary-meta">
                            <div className="meta-item">
                                <span className="meta-label">Claims Analyzed</span>
                                <span className="meta-value">{result.claim_results.length}</span>
                            </div>
                            <div className="meta-item">
                                <span className="meta-label">Formula</span>
                                <span className="meta-value meta-formula">
                                    {result.scoring_breakdown.formula}
                                </span>
                            </div>
                            {result.performance && (
                                <div className="meta-item">
                                    <span className="meta-label">Analysis Time</span>
                                    <span className="meta-value meta-perf">
                                        ⏱ {result.performance.processing_time_ms.toLocaleString()}ms
                                        <span className="perf-detail">
                                            · {result.performance.claims_extracted} claims
                                            · {result.performance.evidence_items_retrieved} sources
                                        </span>
                                    </span>
                                </div>
                            )}
                        </div>
                    </div>

                    {/* Claim Cards */}
                    <div className="claims-list">
                        <h2 className="section-title">Claim Analysis</h2>
                        {result.claim_results.map((cr, i) => (
                            <ReportCard key={i} claimResult={cr} index={i} />
                        ))}
                    </div>

                    {/* Standard disclaimer */}
                    <div className="disclaimer-box">
                        <span className="disclaimer-icon">ℹ</span>
                        {result.disclaimer}
                    </div>

                    <button className="reset-btn full-width" onClick={handleReset}>
                        Analyze Another Text
                    </button>
                </section>
            )}

            {/* ── Footer ───────────────────────────────────── */}
            <footer className="site-footer">
                <p>
                    CrisisVerify · Open-source · MIT License ·{" "}
                    <a href="https://github.com/your-org/crisisverify" target="_blank" rel="noopener noreferrer">
                        GitHub
                    </a>
                </p>
                <p className="footer-note">Not a fact-checking authority. Human review recommended.</p>
            </footer>
        </main>
    );
}
