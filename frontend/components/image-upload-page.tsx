
"use client"

import type React from "react"
import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { Upload, ChevronLeft, ImageIcon, Camera } from "lucide-react"
import CameraCapture from "@/components/camera-capture"

interface ImageUploadPageProps {
  inputData: any
  // pass File, preview URL, and number of recommendations to the parent
  onComplete: (payload: { file: File | null; preview: string; no_recoms: number }) => void
  onBack: () => void
}

export default function ImageUploadPage({ inputData, onComplete, onBack }: ImageUploadPageProps) {
  const [previewImage, setPreviewImage] = useState<string | null>(null)
  const [isDragging, setIsDragging] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [uploadedFile, setUploadedFile] = useState<File | null>(null)
  const [showCameraCapture, setShowCameraCapture] = useState(false)
  const [numRecommendations, setNumRecommendations] = useState<number>(2) // default 3

  const exampleImages = [
    { url: "/example_images/example_1.webp", label: "Example 1" },
    { url: "/example_images/example_2.jpeg", label: "Example 2" },
    { url: "/example_images/example_3.jpg", label: "Example 3" },
  ]

  const handleFileUpload = (file: File) => {
    const reader = new FileReader()
    reader.onload = (event) => {
      const result = event.target?.result as string
      setPreviewImage(result)
      setUploadedFile(file)
      setError(null)
    }
    reader.readAsDataURL(file)
  }

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(true)
  }

  const handleDragLeave = () => setIsDragging(false)

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
    const file = e.dataTransfer.files[0]
    if (file?.type.startsWith("image/")) handleFileUpload(file)
  }

  const handleExampleImageClick = (imageUrl: string) => {
    setPreviewImage(imageUrl)
    setUploadedFile(null)
    setError(null)
  }

  const handleCameraCapture = (imageData: string, file: Blob) => {
    const reader = new FileReader()
    reader.onload = (event) => {
      const result = event.target?.result as string
      setPreviewImage(result)
      setUploadedFile(file as File)
      setError(null)
      setShowCameraCapture(false)
    }
    reader.readAsDataURL(file)
  }

  const dataUrlToFile = async (dataUrl: string): Promise<File> => {
    const res = await fetch(dataUrl)
    const blob = await res.blob()
    const mime = blob.type || "image/jpeg"
    const subtype = mime.split("/")[1] || "jpg"
    const ext = subtype === "jpeg" ? "jpg" : subtype.replace("+xml", "")
    const filename = `example.${ext}`
    return new File([blob], filename, { type: mime })
  }

  const urlToFile = async (url: string): Promise<File> => {
    try {
      const res = await fetch(url)
      const blob = await res.blob()
      const mime = blob.type || "image/jpeg"
      const subtype = mime.split("/")[1] || "jpg"
      const ext = subtype === "jpeg" ? "jpg" : subtype.replace("+xml", "")
      const filename = `example.${ext}`
      return new File([blob], filename, { type: mime })
    } catch (err) {
      if (url.startsWith("data:")) {
        const parts = url.split(",")
        const meta = parts[0]
        const bstr = atob(parts[1])
        let n = bstr.length
        const u8arr = new Uint8Array(n)
        while (n--) u8arr[n] = bstr.charCodeAt(n)
        const mime = meta.split(":")[1].split(";")[0]
        const subtype = mime.split("/")[1] || "jpg"
        const ext = subtype === "jpeg" ? "jpg" : subtype.replace("+xml", "")
        const blob = new Blob([u8arr], { type: mime })
        return new File([blob], `example.${ext}`, { type: mime })
      }
      throw err
    }
  }

  const handleContinue = async () => {
    if (!previewImage) {
      setError("Please upload or choose an example image first")
      return
    }

    setLoading(true)
    setError(null)

    try {
      const fileToSend =
        uploadedFile ||
        (await (previewImage.startsWith("data:") ? dataUrlToFile(previewImage) : urlToFile(previewImage)))

      console.log("Sending recommender payload:", {
        file: fileToSend,
        preview: previewImage,
        no_recoms: numRecommendations,
      })

      onComplete({ file: fileToSend, preview: previewImage, no_recoms: numRecommendations })
    } catch (err) {
      console.error("prepare file error:", err)
      setError(String(err || "Unknown error"))
    } finally {
      setLoading(false)
    }
  }

  if (showCameraCapture) {
    return <CameraCapture onCapture={handleCameraCapture} onCancel={() => setShowCameraCapture(false)} />
  }

  return (
    <div className="min-h-screen bg-background p-4">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <Button onClick={onBack} variant="ghost" className="text-muted-foreground hover:text-foreground -ml-2">
            <ChevronLeft className="w-5 h-5 mr-1" />
            Back
          </Button>
          <h1 className="text-3xl font-bold text-foreground flex-1 text-center">Upload Shelf Image</h1>
          <div className="w-10"></div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Upload Area */}
          <div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* Upload Image Card */}
              <Card className="border-2 border-dashed border-border/50 bg-background/50 hover:border-primary/50 hover:bg-primary/2 transition-all duration-200">
                <label
                  onDragOver={handleDragOver}
                  onDragLeave={handleDragLeave}
                  onDrop={handleDrop}
                  className={`p-12 flex flex-col items-center justify-center cursor-pointer transition-all ${
                    isDragging ? "bg-primary/5 border-primary/80" : ""
                  }`}
                >
                  <div className="w-12 h-12 rounded-lg bg-primary/10 flex items-center justify-center mb-4">
                    <Upload className="w-6 h-6 text-primary" />
                  </div>
                  <h3 className="text-base font-semibold text-foreground mb-2">Drop your image here</h3>
                  <p className="text-sm text-muted-foreground">or click to browse</p>
                  <input
                    type="file"
                    accept="image/*"
                    onChange={(e) => {
                      const file = e.target.files?.[0]
                      if (file) handleFileUpload(file)
                    }}
                    className="hidden"
                  />
                </label>
              </Card>

              {/* Camera Capture Card */}
              <Card
                onClick={() => setShowCameraCapture(true)}
                className="border-2 border-dashed border-border/50 bg-background/50 hover:border-green-500 hover:bg-green-50 transition-all duration-200 flex flex-col items-center justify-center p-12 cursor-pointer"
              >
                <div className="w-12 h-12 rounded-lg bg-green-100 flex items-center justify-center mb-4">
                  <Camera className="w-6 h-6 text-green-600" />
                </div>
                <h3 className="text-base font-semibold text-foreground mb-2">Capture with Camera</h3>
                <p className="text-sm text-muted-foreground">Use device camera</p>
              </Card>
            </div>

            <div className="mt-6">
              <h3 className="text-xs font-semibold text-muted-foreground mb-3 uppercase tracking-wide">
                Example Images for Testing
              </h3>
              <div className="space-y-2">
                {exampleImages.map((example, idx) => (
                  <button
                    key={idx}
                    onClick={() => handleExampleImageClick(example.url)}
                    className="w-full overflow-hidden border border-border/50 rounded-lg hover:border-primary/50 transition-all group"
                  >
                    <div className="flex items-center bg-card hover:bg-primary/2">
                      <div className="w-16 h-16 bg-muted/30 flex-shrink-0 overflow-hidden flex items-center justify-center border-r border-border/30">
                        <img
                          src={example.url || "/placeholder.svg"}
                          alt={example.label}
                          className="w-full h-full object-cover group-hover:scale-105 transition-transform"
                        />
                      </div>
                      <div className="flex-1 px-4 py-3">
                        <p className="text-sm font-medium text-foreground group-hover:text-primary transition-colors">
                          {example.label}
                        </p>
                        <p className="text-xs text-muted-foreground">Click to preview</p>
                      </div>
                      <div className="px-4 text-muted-foreground group-hover:text-primary transition-colors">
                        <ImageIcon className="w-4 h-4" />
                      </div>
                    </div>
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* Preview Area */}
          <div>
            <div className="sticky top-8">
              <h3 className="text-xs font-semibold text-muted-foreground mb-4 uppercase tracking-wide">Preview</h3>
              {previewImage ? (
                <div className="space-y-4">
                  <div className="bg-card border border-border/50 rounded-lg overflow-hidden">
                    <img src={previewImage || "/placeholder.svg"} alt="Preview" className="w-full h-auto" />
                  </div>

                  {error && (
                    <div className="bg-red-50 border border-red-200 rounded-lg p-3">
                      <p className="text-sm text-red-700">{error}</p>
                    </div>
                  )}

                  {/* Number of Recommendations Input */}
                  <div className="flex flex-col space-y-1">
                    <label className="text-xs font-semibold text-muted-foreground">
                      Number of Recommendations
                    </label>
                    <input
                      type="number"
                      min={1}
                      max={100}
                      value={numRecommendations}
                      onChange={(e) => setNumRecommendations(Number(e.target.value))}
                      className="border border-border/50 rounded-lg p-2 text-sm w-full"
                    />
                  </div>

                  <Button
                    onClick={handleContinue}
                    disabled={loading || !previewImage}
                    className="w-full bg-primary hover:bg-primary/90 text-primary-foreground text-sm font-medium h-10 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {loading ? "Analyzing..." : "Analyze Image"}
                  </Button>
                  <Button
                    onClick={() => {
                      setPreviewImage(null)
                      setUploadedFile(null)
                      setError(null)
                    }}
                    variant="outline"
                    className="w-full text-sm font-medium h-10"
                    disabled={loading}
                  >
                    Clear
                  </Button>
                </div>
              ) : (
                <div className="bg-background border-2 border-dashed border-border/50 rounded-lg p-12 text-center">
                  <div className="w-10 h-10 rounded-lg bg-muted/50 flex items-center justify-center mx-auto mb-3">
                    <ImageIcon className="w-5 h-5 text-muted-foreground" />
                  </div>
                  <p className="text-sm text-muted-foreground">Preview will appear here</p>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

