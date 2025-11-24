"use client"

import { useState } from "react"
import InputMethodPage from "@/components/input-method-page"
import ImageUploadPage from "@/components/image-upload-page"
import ProcessingPage from "@/components/processing-page"
import ResultsPage from "@/components/results-page"

type Step = "input-method" | "image-upload" | "processing" | "results"

export default function Home() {
  const [currentStep, setCurrentStep] = useState<Step>("input-method")
  const [inputData, setInputData] = useState<any>(null)
  const [uploadedImage, setUploadedImage] = useState<string | null>(null)
  const [uploadedFile, setUploadedFile] = useState<File | null>(null)
  const [preloadedRecom, setPreloadedRecom] = useState<any[] | null>(null)
  const [numRecommendations, setNumRecommendations] = useState<number>(2)


  const handleInputMethodComplete = (data: any) => {
    setInputData(data)
    setCurrentStep("image-upload")
  }

  // now receives { file, preview }
  const handleImageUploadComplete = (payload: { file: File | null; preview: string; no_recoms?: number }) => {
    setUploadedFile(payload?.file || null)
    setUploadedImage(payload?.preview || null)
    if (payload?.no_recoms) setNumRecommendations(payload.no_recoms)
    setCurrentStep("processing")
  }

  const handleProcessingComplete = (finalImageUrl: string | null, recom: any[]) => {
    setUploadedImage(finalImageUrl)
    setPreloadedRecom(recom || null)
    setCurrentStep("results")
  }

  const handleReset = () => {
    setCurrentStep("input-method")
    setInputData(null)
    setUploadedImage(null)
  }

  return (
    <main className="min-h-screen bg-background">
      {currentStep === "input-method" && <InputMethodPage onComplete={handleInputMethodComplete} />}
      {currentStep === "image-upload" && (
        <ImageUploadPage
          inputData={inputData}
          onComplete={handleImageUploadComplete}
          onBack={() => setCurrentStep("input-method")}
        />
      )}
      {currentStep === "processing" && (
        <ProcessingPage
          inputData={inputData}
          imagePath={uploadedImage}
          no_recoms={numRecommendations}
          uploadedFile={uploadedFile}
          onComplete={handleProcessingComplete}
          onBack={() => setCurrentStep("image-upload")}
        />
      )}

      {currentStep === "results" && (
        <ResultsPage
          inputData={inputData}
          imagePath={uploadedImage}
          onReset={handleReset}
          preloadedRecom={preloadedRecom || undefined}
        />
      )}
    </main>
  )
}
