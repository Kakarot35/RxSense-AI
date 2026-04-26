import { useState } from "react"
import axios from "axios"

interface DrugExplanation {
    drug: string
    dosage: string | null
    frequency: string | null
    explanation: string
    confidence: number
    sources: string[]
    warning: string | null
}

interface InteractionAlert {
    drugs: string[]
    severity: string
    description: string
}

interface ApiResponse {
    entities_found: number
    drugs: DrugExplanation[]
    interactions: InteractionAlert[]
    disclaimer: string
}

const SEVERITY_COLOR: Record<string, string> = {
    Major: "#dc2626",
    Moderate: "#d97706",
    Minor: "#65a30d",
}

export default function App() {
    const [text, setText] = useState("")
    const [result, setResult] = useState<ApiResponse | null>(null)
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState("")

    const submit = async () => {
        if (!text.trim()) return
        setLoading(true)
        setError("")
        setResult(null)
        try {
            const { data } = await axios.post<ApiResponse>("/api/v1/prescriptions/text", { text })
            setResult(data)
        } catch (e: any) {
            setError(e.response?.data?.detail || "Something went wrong.")
        } finally {
            setLoading(false)
        }
    }

    return (
        <div style={{ maxWidth: 720, margin: "40px auto", padding: "0 20px", fontFamily: "system-ui, sans-serif" }}>
            <h1 style={{ fontSize: 24, fontWeight: 600, marginBottom: 8 }}>
                Prescription Explainer
            </h1>
            <p style={{ color: "#6b7280", marginBottom: 24 }}>
                Paste your prescription text below for a plain-language explanation.
            </p>

            <textarea
                value={text}
                onChange={e => setText(e.target.value)}
                placeholder={"Amoxicillin 500mg twice daily\nMetformin 850mg once daily with meals"}
                rows={5}
                style={{
                    width: "100%", padding: 12, borderRadius: 8, border: "1px solid #d1d5db",
                    fontSize: 14, resize: "vertical", boxSizing: "border-box"
                }}
            />

            <button
                onClick={submit}
                disabled={loading || !text.trim()}
                style={{
                    marginTop: 12, padding: "10px 24px", background: "#2563eb", color: "#fff",
                    border: "none", borderRadius: 8, fontSize: 14, cursor: "pointer",
                    opacity: loading ? 0.6 : 1
                }}
            >
                {loading ? "Analysing…" : "Explain Prescription"}
            </button>

            {error && (
                <div style={{
                    marginTop: 16, padding: 12, background: "#fee2e2",
                    borderRadius: 8, color: "#991b1b", fontSize: 14
                }}>
                    {error}
                </div>
            )}

            {result && (
                <div style={{ marginTop: 32 }}>
                    {/* Interaction alerts — show first for safety */}
                    {result.interactions.length > 0 && (
                        <div style={{ marginBottom: 24 }}>
                            <h2 style={{ fontSize: 16, fontWeight: 600, marginBottom: 12 }}>
                                Interaction Alerts
                            </h2>
                            {result.interactions.map((alert, i) => (
                                <div key={i} style={{
                                    padding: 12, borderRadius: 8, marginBottom: 8,
                                    background: "#fef2f2", borderLeft: `4px solid ${SEVERITY_COLOR[alert.severity] ?? "#6b7280"}`
                                }}>
                                    <span style={{ fontWeight: 600, color: SEVERITY_COLOR[alert.severity], fontSize: 13 }}>
                                        {alert.severity}
                                    </span>
                                    <span style={{ marginLeft: 8, fontSize: 13, color: "#374151" }}>
                                        {alert.drugs.join(" + ")}
                                    </span>
                                    <p style={{ margin: "6px 0 0", fontSize: 13, color: "#6b7280" }}>
                                        {alert.description}
                                    </p>
                                </div>
                            ))}
                        </div>
                    )}

                    {/* Drug explanations */}
                    {result.drugs.map((drug, i) => (
                        <div key={i} style={{
                            marginBottom: 20, padding: 20, borderRadius: 12,
                            border: "1px solid #e5e7eb", background: "#fff"
                        }}>
                            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                                <div>
                                    <h3 style={{ margin: 0, fontSize: 18, fontWeight: 600, textTransform: "capitalize" }}>
                                        {drug.drug}
                                    </h3>
                                    {(drug.dosage || drug.frequency) && (
                                        <p style={{ margin: "4px 0 0", fontSize: 13, color: "#6b7280" }}>
                                            {[drug.dosage, drug.frequency].filter(Boolean).join(" · ")}
                                        </p>
                                    )}
                                </div>
                                <span style={{
                                    fontSize: 12, color: "#9ca3af", background: "#f3f4f6",
                                    padding: "3px 8px", borderRadius: 12
                                }}>
                                    {Math.round(drug.confidence * 100)}% confidence
                                </span>
                            </div>
                            <p style={{ marginTop: 16, fontSize: 14, lineHeight: 1.7, color: "#374151", whiteSpace: "pre-wrap" }}>
                                {drug.explanation}
                            </p>
                            {drug.warning && (
                                <p style={{ marginTop: 8, fontSize: 12, color: "#d97706" }}>
                                    ⚠ {drug.warning}
                                </p>
                            )}
                            <p style={{ marginTop: 8, fontSize: 12, color: "#9ca3af" }}>
                                Sources: {drug.sources.join(", ")}
                            </p>
                        </div>
                    ))}

                    {/* Disclaimer */}
                    <p style={{
                        fontSize: 12, color: "#9ca3af", borderTop: "1px solid #e5e7eb",
                        paddingTop: 16, lineHeight: 1.6
                    }}>
                        {result.disclaimer}
                    </p>
                </div>
            )}
        </div>
    )
}
