"use client"

import type React from "react"
import { useState, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { Upload, Database, Type, Camera, X } from "lucide-react"
import { getBookDatabase, uploadCoverImage, selectBookByIsbn, submitMetadata } from "@/lib/api"
import CameraCapture from "./camera-capture"

interface InputMethodPageProps {
  onComplete: (data: any) => void
}

export default function InputMethodPage({ onComplete }: InputMethodPageProps) {
  const [selectedMethod, setSelectedMethod] = useState<string | null>(null)
  const [formData, setFormData] = useState({
    title: "",
    authors: "",
  })
  const [searchQuery, setSearchQuery] = useState("")
  const [showSearchResults, setShowSearchResults] = useState(false)
  const [useTextFallback, setUseTextFallback] = useState(false)
  const [loading, setLoading] = useState(false)
  const [allBooks, setAllBooks] = useState<any[]>([])
  const [showCameraCapture, setShowCameraCapture] = useState(false)
  const [selectedBook, setSelectedBook] = useState<any | null>(null)
  const [previewImage, setPreviewImage] = useState<string | null>(null); // immediate preview
  const [processingImage, setProcessingImage] = useState(false); // backend processing

  useEffect(() => {
    const fetchBooks = async () => {
      setLoading(true)
      const response = await getBookDatabase()
      if (response.success && response.data) {
        setAllBooks(response.data)
      }
      setLoading(false)
    }
    fetchBooks()
  }, [])

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setSelectedMethod("upload");

    // Show preview immediately
    const reader = new FileReader();
    reader.onload = (event) => {
      setPreviewImage(event.target?.result as string);
    };
    reader.readAsDataURL(file);

    // Start backend processing
    (async () => {
      setProcessingImage(true);
      try {
        const res = await uploadCoverImage(file);
        // Here you can call onComplete with backend response
        if (res.success && res.data) {
          onComplete({ method: "upload", data: res.data, filename: file.name, file });
        } else {
          onComplete({ method: "upload", data: reader.result, filename: file.name, file });
        }
      } catch (err) {
        console.error("Upload failed:", err);
        onComplete({ method: "upload", data: reader.result, filename: file.name, file });
      } finally {
        setProcessingImage(false); // hide loader
      }
    })();
  };

  const handleCameraCapture = (imageData: string, file: Blob) => {
    // Show preview immediately
    setPreviewImage(imageData);
    setSelectedMethod("camera");

    // Start backend processing
    (async () => {
      setProcessingImage(true);
      try {
        const res = await uploadCoverImage(file as File);
        if (res.success && res.data) {
          onComplete({
            method: "camera",
            data: res.data,
            file: file,
            filename: `camera-capture-${Date.now()}.jpg`,
          });
        } else {
          // fallback to base64 image
          onComplete({
            method: "camera",
            data: imageData,
            file: file,
            filename: `camera-capture-${Date.now()}.jpg`,
          });
        }
      } catch (err) {
        console.error("Camera upload failed:", err);
        onComplete({
          method: "camera",
          data: imageData,
          file: file,
          filename: `camera-capture-${Date.now()}.jpg`,
        });
      } finally {
        setProcessingImage(false);
      }
    })();
  };

  const filteredBooks = allBooks.filter((book) => {
    const title = (book?.title || book?.Title || "")
    const authors = (book?.authors || book?.author || "")
    const q = searchQuery.toLowerCase()
    return title.toLowerCase().includes(q) || authors.toLowerCase().includes(q)
  })

  const handleDatabaseSelect = async (book: (typeof allBooks)[0]) => {
    try {
      if (book?.isbn) {
        const res = await selectBookByIsbn(book.isbn)
        if (!res.success) {
          console.error("selectBookByIsbn failed:", res.error)
        }
      }
    } catch (err) {
      console.error("Error calling selectBookByIsbn:", err)
    }

    onComplete({
      method: "database",
      data: book.image_link || book.image,
      bookInfo: book,
    })
  }

  const handleMetadataSubmit = async () => {
    if (!formData.title || !formData.authors) return
    setLoading(true)
    try {
      const res = await submitMetadata({ title: formData.title, author: formData.authors })
      if (res.success) {
        onComplete({ method: "metadata", data: res.data || { title: formData.title, author: formData.authors } })
      } else {
        console.error("submitMetadata failed:", res.error)
        onComplete({ method: "metadata", data: { title: formData.title, author: formData.authors } })
      }
    } catch (err) {
      console.error("Error calling submitMetadata:", err)
      onComplete({ method: "metadata", data: { title: formData.title, author: formData.authors } })
    } finally {
      setLoading(false)
    }
  }

  if (showCameraCapture) {
    return <CameraCapture onCapture={handleCameraCapture} onCancel={() => setShowCameraCapture(false)} />
  }

  return (
    <div className="min-h-screen bg-background flex items-center justify-center p-4">
      <div className="max-w-5xl w-full">
        {/* Header */}
        <div className="mb-16 text-center">
          <h1 className="text-5xl font-bold text-foreground mb-3 tracking-tight">Book Vision</h1>
          <p className="text-muted-foreground text-base">Select an input method to get started</p>
        </div>

        {/* Options Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-4 gap-5">
          {/* Option 1: Direct Upload */}
          <Card
            className="relative border border-border/50 bg-card hover:border-primary/60 hover:shadow-sm transition-all duration-200 cursor-pointer group"
            onClick={() => document.getElementById("file-upload")?.click()}
          >
            {/* Image Preview with optional blur */}
            {previewImage && selectedMethod === "upload" && (
              <img
                src={previewImage}
                alt="Preview"
                className={`absolute inset-0 w-full h-full object-cover rounded-2xl transition-all duration-300 ${
                  processingImage ? "filter blur-sm" : ""
                }`}
              />
            )}

            {/* Bottom-left Loading Overlay */}
            {processingImage && selectedMethod === "upload" && (
              <div className="absolute bottom-2 left-2 bg-black/50 text-white text-xs px-2 py-1 rounded-md backdrop-blur-sm flex items-center gap-2 z-20">
                <svg
                  className="animate-spin h-4 w-4 text-white"
                  xmlns="http://www.w3.org/2000/svg"
                  fill="none"
                  viewBox="0 0 24 24"
                >
                  <circle
                    className="opacity-25"
                    cx="12"
                    cy="12"
                    r="10"
                    stroke="currentColor"
                    strokeWidth="4"
                  ></circle>
                  <path
                    className="opacity-75"
                    fill="currentColor"
                    d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z"
                  ></path>
                </svg>
                Processing...
              </div>
            )}

            {/* Card Content */}
            <div className="p-8 flex flex-col items-center justify-center h-full">
              <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center mb-4 group-hover:bg-primary/15 transition-colors">
                <Upload className="w-5 h-5 text-primary" />
              </div>
              <h2 className="text-lg font-semibold text-foreground mb-2">Upload Cover</h2>
              <p className="text-muted-foreground text-sm text-center leading-relaxed">
                Upload a book cover image
              </p>
            </div>

            <input
              id="file-upload"
              type="file"
              accept="image/*"
              onChange={handleFileUpload}
              className="hidden"
            />
          </Card>


          {/* Option 2: Camera Capture */}
          <Card
            className="relative border border-border/50 bg-card hover:border-primary/60 hover:shadow-sm transition-all duration-200 cursor-pointer group"
            onClick={() => setShowCameraCapture(true)}
          >
            {/* Camera Preview with optional blur */}
          {previewImage && selectedMethod === "camera" && (
            <img
              src={previewImage}
              alt="Camera Preview"
              className={`absolute inset-0 w-full h-full object-cover rounded-2xl transition-all duration-300 ${
                processingImage ? "filter blur-sm" : ""
              }`}
            />
          )}

          {/* Top-right / corner Processing Overlay */}
          {processingImage && selectedMethod === "camera" && (
            <div className="absolute bottom-2 left-2 bg-black/50 text-white text-xs px-2 py-1 rounded-md backdrop-blur-sm flex items-center gap-2 z-20">
              <svg
                className="animate-spin h-4 w-4 text-white"
                xmlns="http://www.w3.org/2000/svg"
                fill="none"
                viewBox="0 0 24 24"
              >
                <circle
                  className="opacity-25"
                  cx="12"
                  cy="12"
                  r="10"
                  stroke="currentColor"
                  strokeWidth="4"
                ></circle>
                <path
                  className="opacity-75"
                  fill="currentColor"
                  d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z"
                ></path>
              </svg>
              Processing...
            </div>
          )}


            {/* Card Content */}
            <div className="p-8 flex flex-col items-center justify-center h-full">
              <div className="w-10 h-10 rounded-lg bg-green-500/10 flex items-center justify-center mb-4 group-hover:bg-green-500/15 transition-colors">
                <Camera className="w-5 h-5 text-green-600" />
              </div>
              <h2 className="text-lg font-semibold text-foreground mb-2">Camera</h2>
              <p className="text-muted-foreground text-sm text-center leading-relaxed">
                Capture with your device camera
              </p>
            </div>
          </Card>

          {/* Option 2: Database */}
          <Card className="border border-border/50 bg-card">
            <div className="p-8">
              <div className="w-10 h-10 rounded-lg bg-accent/10 flex items-center justify-center mb-4 mx-auto">
                <Database className="w-5 h-5 text-accent" />
              </div>
              <h2 className="text-lg font-semibold text-foreground mb-4 text-center">From Database</h2>

              <div className="space-y-3">
                <div className="relative">
                  <input
                    type="text"
                    placeholder={loading ? "Loading books..." : "Search books..."}
                    value={searchQuery}
                    onChange={(e) => {
                      setSearchQuery(e.target.value)
                      setShowSearchResults(true)
                    }}
                    onFocus={() => setShowSearchResults(true)}
                    disabled={loading}
                    className="w-full px-3 py-2.5 bg-background border border-border/50 rounded-lg text-foreground text-sm placeholder:text-muted-foreground/50 focus:outline-none focus:border-primary/50 focus:ring-1 focus:ring-primary/20 transition-all disabled:opacity-50"
                  />
                  {searchQuery && (
                    <button
                      onClick={() => {
                        setSearchQuery("")
                        setShowSearchResults(false)
                      }}
                      className="absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                    >
                      <X className="w-4 h-4" />
                    </button>
                  )}
                </div>

                {/* Search Results Dropdown */}
                {showSearchResults && !loading && (
                  <div className="bg-card border border-border/50 rounded-lg overflow-hidden max-h-48 overflow-y-auto shadow-lg">
                    {filteredBooks.length > 0 ? (
                      <div className="space-y-0">
                        {filteredBooks.map((book) => (
                          <button
                            key={book.isbn || book.title}
                            onClick={() => {
                              // Select the book but don't submit yet — user must confirm
                              setSelectedBook(book)
                              setShowSearchResults(false)
                            }}
                            className={
                              "w-full px-3 py-2.5 text-left border-b border-border/30 last:border-b-0 transition-colors group " +
                              (selectedBook && (selectedBook.isbn || selectedBook.title) === (book.isbn || book.title)
                                ? "bg-primary/5"
                                : "hover:bg-primary/5")
                            }
                          >
                            <p className="text-sm font-medium text-foreground group-hover:text-primary">{book.title}</p>
                            <p className="text-xs text-muted-foreground">{book.authors || book.author}</p>
                          </button>
                        ))}
                      </div>
                    ) : searchQuery ? (
                      <div className="p-4 text-center">
                        <p className="text-xs text-muted-foreground mb-3">No books found</p>
                        <button
                          onClick={() => setUseTextFallback(true)}
                          className="text-xs text-primary hover:text-primary/80 font-medium"
                        >
                          Use text input instead
                        </button>
                      </div>
                    ) : (
                      <div className="p-4 text-center">
                        <p className="text-xs text-muted-foreground">Start typing to search...</p>
                      </div>
                    )}
                  </div>
                )}

                {/* Selected book preview + submit */}
                {selectedBook && (
                  <div className="mt-3 p-3 border border-border/40 rounded-lg bg-background">
                  <p className="text-sm font-medium text-foreground">Selected</p>
                  <p className="text-sm text-foreground/90">{selectedBook.title}</p>
                  <p className="text-xs text-muted-foreground mb-3">{selectedBook.authors || selectedBook.author}</p>

                  <div className="flex gap-2 flex-wrap">
                    <Button
                      onClick={async () => {
                        setLoading(true)
                        try {
                          await handleDatabaseSelect(selectedBook)
                        } catch (err) {
                          console.error("submit selected book error:", err)
                        } finally {
                          setLoading(false)
                        }
                      }}
                      className="flex-1 bg-primary hover:bg-primary/90 text-primary-foreground text-sm font-medium h-8"
                      disabled={loading}
                    >
                      {loading ? "Submitting..." : "Submit"}
                    </Button>
                    <Button
                      onClick={() => setSelectedBook(null)}
                      className="flex-1 bg-green-600 hover:bg-green-700 text-white text-sm font-medium h-8"
                    >
                      Cancel
                    </Button>

                    </div>
                  </div>
                )}

                {filteredBooks.length === 0 && searchQuery && !useTextFallback && (
                  <p className="text-xs text-muted-foreground text-center">
                    No matches. Use "Enter Details" tab instead.
                  </p>
                )}
              </div>
            </div>
          </Card>

          {/* Option 4: Metadata Input */}
        <Card className="border border-border/50 bg-card">
          <div className="p-8">
            <div className="w-10 h-10 rounded-lg bg-blue-500/10 flex items-center justify-center mx-auto mb-4">
              <Type className="w-5 h-5 text-blue-600" />
            </div>
            <h2 className="text-lg font-semibold text-foreground mb-4 text-center">Enter Details</h2>
            <div className="space-y-3">
              <div>
                <label className="text-xs uppercase tracking-wide text-muted-foreground block mb-2 font-medium">
                  Title
                </label>
                <input
                  type="text"
                  placeholder="Book title"
                  value={formData.title}
                  onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                  className="w-full px-3 py-2.5 bg-background border border-border/50 rounded-lg text-foreground text-sm placeholder:text-muted-foreground/50 focus:outline-none focus:border-primary/50 focus:ring-1 focus:ring-primary/20 transition-all"
                />
              </div>
              <div>
                <label className="text-xs uppercase tracking-wide text-muted-foreground block mb-2 font-medium">
                  Authors
                </label>
                <input
                  type="text"
                  placeholder="Author names"
                  value={formData.authors}
                  onChange={(e) => setFormData({ ...formData, authors: e.target.value })}
                  className="w-full px-3 py-2.5 bg-background border border-border/50 rounded-lg text-foreground text-sm placeholder:text-muted-foreground/50 focus:outline-none focus:border-primary/50 focus:ring-1 focus:ring-primary/20 transition-all"
                />
              </div>
              <Button
                onClick={handleMetadataSubmit}
                className="w-full mt-4 bg-primary hover:bg-primary/90 text-primary-foreground text-sm font-medium h-10"
                disabled={!formData.title || !formData.authors || loading} // disabled while loading
              >
                {loading ? "Submitting..." : "Submit"}  {/* show loading text */}
              </Button>
            </div>
          </div>
        </Card>
        </div>
      </div>
    </div>
  )
}