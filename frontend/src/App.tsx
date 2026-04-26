import { useState } from "react"
import axios from "axios"
import { usePrescription } from "./hooks/usePrescription"

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
    audio_url?: string
}

const SEVERITY_COLOR: Record<string, string> = {
    Major: "#dc2626",
    Moderate: "#d97706",
    Minor: "#65a30d",
}

export default function App() {
    const [text, setText] = useState("")
    const [imageFile, setImageFile] = useState<File | null>(null)
    const [isHandwritten, setIsHandwritten] = useState(false)
    const [imageUploading, setImageUploading] = useState(false)

    // Used for direct OCR responses (which don't use Celery yet in this iteration)
    const [directResult, setDirectResult] = useState<ApiResponse | null>(null)
    const [directError, setDirectError] = useState("")

    const { status, step, result: celeryResult, error: celeryError, submit } = usePrescription()

    const result = celeryResult || directResult
    const error = celeryError || directError
    const loading = status === "queued" || status === "processing" || imageUploading

    const handleTextSubmit = () => {
        setDirectResult(null)
        setDirectError("")
        setImageFile(null)
        submit(text)
    }

    const handleImageSubmit = async () => {
        if (!imageFile) return
        setDirectResult(null)
        setDirectError("")
        setImageUploading(true)
        
        const formData = new FormData()
        formData.append("file", imageFile)
        formData.append("handwritten", String(isHandwritten))

        try {
            const { data } = await axios.post<ApiResponse>("/api/v1/prescriptions/image", formData)
            setDirectResult(data)
        } catch (e: any) {
            setDirectError(e.response?.data?.detail || "Failed to process image.")
        } finally {
            setImageUploading(false)
        }
    }

    return (
        <div style={{ maxWidth: 720, margin: "40px auto", padding: "0 20px", fontFamily: "system-ui, sans-serif" }}>
            <h1 style={{ fontSize: 24, fontWeight: 600, marginBottom: 8 }}>
                Prescription Explainer
            </h1>
            <p style={{ color: "#6b7280", marginBottom: 24 }}>
                Paste text or upload a prescription image.
            </p>

            <div style={{ display: "flex", gap: "20px", marginBottom: "20px", flexWrap: "wrap" }}>
                <div style={{ flex: 1, minWidth: "300px" }}>
                    <h3 style={{ fontSize: 16, marginBottom: 8 }}>Option 1: Text</h3>
                    <textarea
                        value={text}
                        onChange={e => setText(e.target.value)}
                        placeholder={"Amoxicillin 500mg twice daily"}
                        rows={5}
                        style={{
                            width: "100%", padding: 12, borderRadius: 8, border: "1px solid #d1d5db",
                            fontSize: 14, resize: "vertical", boxSizing: "border-box"
                        }}
                    />
                    <button
                        onClick={handleTextSubmit}
                        disabled={loading || !text.trim()}
                        style={{
                            marginTop: 12, padding: "10px 24px", background: "#2563eb", color: "#fff",
                            border: "none", borderRadius: 8, fontSize: 14, cursor: "pointer",
                            opacity: (loading || !text.trim()) ? 0.6 : 1
                        }}
                    >
                        {status === "processing" ? `Analysing (${step})...` : "Explain Text"}
                    </button>
                </div>

                <div style={{ flex: 1, minWidth: "300px" }}>
                    <h3 style={{ fontSize: 16, marginBottom: 8 }}>Option 2: Image Upload</h3>
                    <input 
                        type="file" 
                        accept="image/jpeg, image/png, image/webp, application/pdf"
                        onChange={(e) => setImageFile(e.target.files?.[0] || null)}
                        style={{ marginBottom: 12, display: "block" }}
                    />
                    <label style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 14, marginBottom: 12 }}>
                        <input 
                            type="checkbox" 
                            checked={isHandwritten} 
                            onChange={(e) => setIsHandwritten(e.target.checked)} 
                        />
                        Handwritten prescription
                    </label>
                    <button
                        onClick={handleImageSubmit}
                        disabled={loading || !imageFile}
                        style={{
                            padding: "10px 24px", background: "#10b981", color: "#fff",
                            border: "none", borderRadius: 8, fontSize: 14, cursor: "pointer",
                            opacity: (loading || !imageFile) ? 0.6 : 1
                        }}
                    >
                        {imageUploading ? "Processing Image..." : "Explain Image"}
                    </button>
                </div>
            </div>

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
                    
                    <div style={{ display: "flex", gap: "10px", marginBottom: "20px" }}>
                       {/* Audio and PDF buttons could go here. For now we check if audio is returned */}
                       {result.audio_url && (
                           <audio controls src={`http://localhost:8000${result.audio_url}`} style={{ height: "40px" }} />
                       )}
                    </div>

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
