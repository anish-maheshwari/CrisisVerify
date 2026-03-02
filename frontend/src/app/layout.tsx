import type { Metadata } from "next";
import "@/app/globals.css";

export const metadata: Metadata = {
    title: "CrisisVerify — Structured Claim Verification",
    description:
        "AI-assisted structured claim verification for crisis scenarios. Not a fact-checking authority. Human review recommended.",
    keywords: ["fact-check", "crisis", "misinformation", "verification", "civic tech"],
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
    return (
        <html lang="en">
            <head>
                <link rel="preconnect" href="https://fonts.googleapis.com" />
                <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
                <link
                    href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap"
                    rel="stylesheet"
                />
            </head>
            <body>{children}</body>
        </html>
    );
}
