import { useState, useRef } from "react"
import axios from "axios"

export function usePrescription() {
  const [status, setStatus] = useState<"idle"|"queued"|"processing"|"complete"|"failed">("idle")
  const [step, setStep] = useState("")
  const [result, setResult] = useState<any>(null)
  const [error, setError] = useState("")
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const submit = async (text: string) => {
    setStatus("queued")
    setError("")
    setResult(null)

    try {
        const { data } = await axios.post("/api/v1/prescriptions/submit", { text })
        const jobId: string = data.job_id

        pollRef.current = setInterval(async () => {
          try {
            const { data: job } = await axios.get(`/api/v1/prescriptions/jobs/${jobId}`)
            setStep(job.step ?? "")
            setStatus(job.status)
            if (job.status === "complete") {
              clearInterval(pollRef.current!)
              setResult(job.result)
            }
            if (job.status === "failed") {
              clearInterval(pollRef.current!)
              setError(job.error ?? "Processing failed.")
            }
          } catch (err: any) {
              clearInterval(pollRef.current!)
              setStatus("failed")
              setError(err.response?.data?.detail || "Error polling status.")
          }
        }, 1500)   // poll every 1.5 seconds
    } catch (err: any) {
        setStatus("failed")
        setError(err.response?.data?.detail || "Failed to submit prescription.")
    }
  }

  return { status, step, result, error, submit }
}
