"use client"

import { useRef, useState, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { RotateCcw, Check, X, Camera } from "lucide-react"

interface CameraCaptureProps {
  onCapture: (imageData: string, file: Blob) => void
  onCancel: () => void
}

export default function CameraCapture({ onCapture, onCancel }: CameraCaptureProps) {
  const videoRef = useRef<HTMLVideoElement>(null)
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const streamRef = useRef<MediaStream | null>(null)
  const [capturedImage, setCapturedImage] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // startCamera is exposed so retry can reinitialize the camera if needed
  const startCamera = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: "environment", width: { ideal: 1280 }, height: { ideal: 720 } },
      })
      streamRef.current = stream
      if (videoRef.current) {
        videoRef.current.srcObject = stream
      }
      setLoading(false)
    } catch (err) {
      setError("Unable to access camera. Please check permissions.")
      setLoading(false)
    }
  }

  const [cameraKey, setCameraKey] = useState(0)

  useEffect(() => {
    startCamera()
    return () => {
      if (streamRef.current) {
        streamRef.current.getTracks().forEach((t) => t.stop())
        streamRef.current = null
      }
      if (videoRef.current) videoRef.current.srcObject = null
    }
  }, [cameraKey])

  const handleCancel = () => {
    // Stop camera immediately
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((t) => t.stop())
      streamRef.current = null
    }
    if (videoRef.current) {
      videoRef.current.srcObject = null
    }
    // Then call parent cancel handler
    onCancel()
  }

  const handleCapture = () => {
    if (videoRef.current && canvasRef.current) {
      const context = canvasRef.current.getContext("2d")
      if (context) {
        canvasRef.current.width = videoRef.current.videoWidth
        canvasRef.current.height = videoRef.current.videoHeight
        context.drawImage(videoRef.current, 0, 0)
        const imageData = canvasRef.current.toDataURL("image/jpeg", 0.95)
        setCapturedImage(imageData)
      }
    }
  }

  const handleRetry = () => {
    setCapturedImage(null)
    setError(null)
    setCameraKey((k) => k + 1)
  }


  const handleSubmit = async () => {
    if (!capturedImage) return;

    setLoading(true);  // start loading immediately
    setError(null);

    try {
      const blob = await new Promise<Blob | null>((resolve) =>
        canvasRef.current?.toBlob(resolve, "image/jpeg", 0.95)
      );

      if (!blob) {
        setError("Failed to create image blob");
        setLoading(false); // only stop loading if blob fails
        return;
      }

      const file = new File([blob], "camera-capture.jpg", { type: "image/jpeg" });

      // Call parent handler, let parent navigate
      await onCapture(capturedImage, file);

      // Do NOT call setLoading(false) here; parent should stop loading when page changes
    } catch (err) {
      console.error(err);
      setError(String(err || "Unknown error"));
      setLoading(false); // stop loading on error
    }
  };

  const handleSubmitAndClose = async () => {
    await handleSubmit()
    handleCancel() // stop camera after submit
  }

  return (
    <div className="min-h-screen bg-background flex items-center justify-center p-4">
      <div className="w-full max-w-2xl">
        <div className="mb-8 text-center">
          <h1 className="text-3xl font-bold text-foreground mb-2">Capture Book Image</h1>
          <p className="text-muted-foreground text-sm">Position the book cover clearly in view</p>
        </div>

        <Card className="border border-border/50 bg-card overflow-hidden">
          {/* Camera View / Captured Image */}
          <div className="relative aspect-video bg-black flex items-center justify-center overflow-hidden">
            {!capturedImage ? (
              <>
                {loading ? (
                  <div className="flex flex-col items-center gap-3">
                    <div className="w-8 h-8 border-2 border-primary border-t-transparent rounded-full animate-spin"></div>
                    <p className="text-sm text-muted-foreground">Initializing camera...</p>
                  </div>
                ) : error ? (
                  <div className="text-center p-6">
                    <p className="text-red-500 text-sm mb-4">{error}</p>
                    <Button onClick={onCancel} variant="outline">
                      Back
                    </Button>
                  </div>
                ) : (
                  <video
                    ref={videoRef}
                    autoPlay
                    playsInline
                    className="w-full h-full object-cover"
                    style={{ WebkitTransform: "scaleX(-1)", transform: "scaleX(-1)" }}
                  />
                )}
              </>
            ) : (
              <img src={capturedImage || "/placeholder.svg"} alt="Captured" className="w-full h-full object-contain" />
            )}

            {/* Corner guides */}
            {!capturedImage && !loading && !error && (
              <div className="absolute inset-0 pointer-events-none">
                <div className="absolute top-4 left-4 w-8 h-8 border-2 border-primary/50"></div>
                <div className="absolute top-4 right-4 w-8 h-8 border-2 border-primary/50"></div>
                <div className="absolute bottom-4 left-4 w-8 h-8 border-2 border-primary/50"></div>
                <div className="absolute bottom-4 right-4 w-8 h-8 border-2 border-primary/50"></div>
              </div>
            )}
          </div>

          {/* Canvas for image capture */}
          <canvas ref={canvasRef} className="hidden" />

          {/* Controls */}
          <div className="p-6 flex items-center justify-center gap-3">
            {!capturedImage ? (
              <>
                {/* <Button onClick={onCancel} variant="outline" className="flex-1 h-10 bg-transparent">
                  <X className="w-4 h-4 mr-2" />
                  Cancel
                </Button> */}
                <Button onClick={handleCancel} variant="outline" className="flex-1 h-10 bg-transparent">
                  <X className="w-4 h-4 mr-2" />
                  Cancel
                </Button>
                <Button
                  onClick={handleCapture}
                  disabled={loading || !!error}
                  className="flex-1 h-10 bg-primary hover:bg-primary/90"
                >
                  <Camera className="w-4 h-4 mr-2" />
                  Capture
                </Button>
              </>
            ) : (
              <>
                <Button onClick={handleRetry} variant="outline" className="flex-1 h-10 bg-transparent">
                  <RotateCcw className="w-4 h-4 mr-2" />
                  Retry
                </Button>
                <Button
                onClick={handleSubmitAndClose}
                className="flex-1 h-10 bg-primary hover:bg-primary/90"
                disabled={loading}
                >
                {loading ? "Submitting..." : <><Check className="w-4 h-4 mr-2" />Submit</>}
              </Button>
              </>
            )}
          </div>
        </Card>
      </div>
    </div>
  )
}
