"use client";

import React from "react";

interface InputAreaProps {
    value: string;
    onChange: (val: string) => void;
    onSubmit: () => void;
    isLoading: boolean;
}

export function InputArea({
    value,
    onChange,
    onSubmit,
    isLoading,
}: InputAreaProps) {
    const charCount = value.length;
    const maxChars = 2000;
    const isOverLimit = charCount > maxChars;
    const isEmpty = value.trim().length < 10;

    return (
        <div className="input-card">
            <div className="input-header">
                <label htmlFor="claim-input" className="input-label">
                    Enter Text to Verify
                </label>
                <div className={`char-count ${isOverLimit ? "char-over" : ""}`}>
                    {charCount}/{maxChars}
                </div>
            </div>

            <textarea
                id="claim-input"
                className="claim-textarea"
                placeholder={"Paste a tweet, news headline, or paragraph here…\n\nExample: \"Major dam has collapsed after earthquake in Region X, displacing 50,000 residents.\""}
                value={value}
                onChange={(e) => onChange(e.target.value)}
                rows={6}
                maxLength={maxChars}
                disabled={isLoading}
                aria-label="Text to analyze"
            />

            <div className="input-footer">
                <button
                    className="analyze-btn"
                    onClick={onSubmit}
                    disabled={isLoading || isEmpty || isOverLimit}
                    aria-label="Analyze text"
                >
                    {isLoading ? (
                        <span className="btn-loading">
                            <span className="spinner" />
                            Analyzing…
                        </span>
                    ) : (
                        "Analyze →"
                    )}
                </button>
            </div>
        </div>
    );
}
