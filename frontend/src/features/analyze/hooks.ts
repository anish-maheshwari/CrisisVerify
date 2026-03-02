"use client";

import { useState, useCallback } from "react";
import { AnalysisResult } from "@/types/analysis";
import { analyzeText } from "./api";

export interface UseAnalysisState {
    result: AnalysisResult | null;
    isLoading: boolean;
    error: string | null;
    analyze: (text: string, crisisMode: boolean) => Promise<void>;
    reset: () => void;
}

export function useAnalysis(): UseAnalysisState {
    const [result, setResult] = useState<AnalysisResult | null>(null);
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const analyze = useCallback(async (text: string, crisisMode: boolean) => {
        setIsLoading(true);
        setError(null);
        setResult(null);
        try {
            const data = await analyzeText({ text, crisis_mode: crisisMode });
            setResult(data);
        } catch (err: unknown) {
            setError(err instanceof Error ? err.message : "An unexpected error occurred.");
        } finally {
            setIsLoading(false);
        }
    }, []);

    const reset = useCallback(() => {
        setResult(null);
        setError(null);
    }, []);

    return { result, isLoading, error, analyze, reset };
}
