
"use client"

import { useEffect, useRef, useState } from "react"
import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { Loader2, Check, Clock } from "lucide-react"
import { getRecommenderResults, analyzeShelfImage } from "@/lib/api"

interface Props {
  inputData: any
  imagePath: string | null
  no_recoms: number
  uploadedFile?: File | null 
  onComplete: (finalImageUrl: string | null, recom: any[]) => void
  onBack: () => void
}

type StepState = 'pending' | 'loading' | 'done' | 'error'

export default function ProcessingPage({ inputData, imagePath, no_recoms, uploadedFile, onComplete, onBack }: Props) {
  const [stepFetch, setStepFetch] = useState<StepState>('pending')
  const [stepRecom, setStepRecom] = useState<StepState>('pending')
  const [error, setError] = useState<string | null>(null)
  const [elapsedTime, setElapsedTime] = useState(0) // in seconds

  const abortControllerRef = useRef<AbortController | null>(null)

useEffect(() => {
  let mounted = true;
  console.log("[ProcessingPage] useEffect triggered with:", { imagePath, uploadedFile });

  // Abort controller created outside run(), so cleanup always knows it
  abortControllerRef.current = new AbortController();
  const signal = abortControllerRef.current.signal;

  // TIMER FIXED — always defined here, not inside run()
  let interval: NodeJS.Timeout | null = null;

  // Start timer ONLY if uploadedFile exists
  if (uploadedFile) {
    setElapsedTime(0);
    interval = setInterval(() => {
      if (mounted) {
        setElapsedTime(prev => prev + 1);
      }
    }, 1000);
  }

  const run = async () => {
    try {
      setStepFetch("loading");

      if (!uploadedFile) {
        throw new Error("No file provided for analysis");
      }

      // Step 1—Analyze shelf
      const analyzeRes = await analyzeShelfImage(uploadedFile, { signal });
      if (!mounted) return;
      if (!analyzeRes.success) throw new Error(analyzeRes.error || "shelf analysis failed");
      setStepFetch("done");

      // Step 2—Recommender
      setStepRecom("loading");
      const res = await getRecommenderResults({ recomData: { no_recoms } });
      if (!mounted || signal.aborted) return;
      if (!res.success) throw new Error(res.error || "recommender failed");

      const finalUrl = res.data?.final_image_url || imagePath;
      const recoms = res.data?.recom || [];
      setStepRecom("done");

      // Optional: Small post-processing delay (abortable)
      await new Promise<void>((resolve, reject) => {
        const timeout = setTimeout(resolve, 300);
        signal.addEventListener("abort", () => {
          clearTimeout(timeout);
          reject(new DOMException("Aborted", "AbortError"));
        });
      });

      if (!mounted || signal.aborted) return;
      onComplete(finalUrl, recoms);

    } catch (err: any) {
      if (err.name === "AbortError") {
        console.log("[ProcessingPage] Request aborted");
        return;
      }

      console.error("Processing error", err);
      setError(err.message || "Unknown error");
      setStepFetch(s => (s === "pending" ? "error" : s));
      setStepRecom("error");

    } finally {
      abortControllerRef.current = null;
    }
  };

  run();

  // Cleanup
  return () => {
    mounted = false;
    abortControllerRef.current?.abort();
    if (interval) clearInterval(interval);   // TIMER FIXED
  };
}, [imagePath, inputData, onComplete, uploadedFile]);


  const renderStatus = (state: StepState) => {
    if (state === 'loading') return <Loader2 className="w-4 h-4 animate-spin" />
    if (state === 'done') return <Check className="w-4 h-4 text-green-500" />
    if (state === 'error') return <Clock className="w-4 h-4 text-red-500" />
    return <Clock className="w-4 h-4 text-muted-foreground" />
  }

  const formatTime = (seconds: number) => {
    const m = Math.floor(seconds / 60).toString().padStart(2, '0')
    const s = (seconds % 60).toString().padStart(2, '0')
    return `${m}:${s}`
  }

  return (
    <div className="min-h-screen bg-background p-4">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <Button onClick={onBack} variant="ghost">Back</Button>
          <h1 className="text-2xl font-bold">Processing</h1>
          <div style={{ width: 64 }} />
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Preview Panel */}
          <div className="lg:col-span-2">
            <Card className="p-4">
              <h3 className="text-sm font-semibold mb-3">Preview</h3>
              <div className="bg-card rounded overflow-hidden">
                {imagePath ? (
                  <img src={imagePath} alt="preview" className="w-full h-auto object-contain" />
                ) : (
                  <div className="p-12 text-center text-sm text-muted-foreground">No preview image</div>
                )}
              </div>
            </Card>
          </div>

          {/* Progress Panel */}
          <div>
            <Card className="p-4 relative">
              <h3 className="text-sm font-semibold mb-4">Progress</h3>
              <div className="space-y-4">
                <div className="flex items-center gap-3">
                  {renderStatus(stepFetch)}
                  <div>
                    <div className="text-sm font-medium">Uploading Image & Fetch Data</div>
                    <div className="text-xs text-muted-foreground">Saving shelf metadata / images</div>
                  </div>
                </div>

                <div className="flex items-center gap-3">
                  {renderStatus(stepRecom)}
                  <div>
                    <div className="text-sm font-medium">Recommender Analysis</div>
                    <div className="text-xs text-muted-foreground">Computing similarity & drawing results</div>
                  </div>
                </div>

                {error && (
                  <div className="bg-red-50 border border-red-200 rounded p-3 text-sm text-red-700">{error}</div>
                )}

                <div className="flex gap-2 mt-4">
                  <Button onClick={onBack} variant="outline">Cancel</Button>
                </div>

                {/* Elapsed Timer */}
                <div className="absolute bottom-2 right-4 text-xs text-muted-foreground">
                  Elapsed Time: {formatTime(elapsedTime)}
                </div>
              </div>
            </Card>
          </div>
        </div>
      </div>
    </div>
  )
}

