import { AnalyzeRequest, AnalysisResult, ApiError } from "@/types/analysis";

// Empty string = relative URL → browser calls /api/v1/analyze on same host.
// Apache on EC2 proxies /api/* → backend:8000.
// For local dev: set NEXT_PUBLIC_API_URL=http://localhost:8000 in docker-compose.
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "";

export async function analyzeText(request: AnalyzeRequest): Promise<AnalysisResult> {
    const response = await fetch(`${API_BASE_URL}/api/v1/analyze`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            Accept: "application/json",
        },
        body: JSON.stringify(request),
    });

    if (!response.ok) {
        const errorData: ApiError = await response.json().catch(() => ({
            error: "Request failed",
            detail: `HTTP ${response.status}: ${response.statusText}`,
        }));
        throw new Error(errorData.detail || errorData.error || "Analysis failed");
    }

    return response.json();
}
