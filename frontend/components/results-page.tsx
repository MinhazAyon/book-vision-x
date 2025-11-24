"use client"

import { useEffect, useRef, useState } from "react"
import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { ChevronLeft, Zap, Loader2 } from "lucide-react"
import BookRecommendationCard from "@/components/book-recommendation-card"
import BookDetailsModal from "@/components/book-details-modal"
import { getRecommenderResults } from "@/lib/api"
import Zoom from "react-medium-image-zoom"
import "react-medium-image-zoom/dist/styles.css"

interface ResultsPageProps {
  inputData: any
  imagePath: string | null
  onReset: () => void
  preloadedRecom?: any[]
}

type StepState = 'pending' | 'loading' | 'done' | 'error'

export default function ResultsPage({ inputData, imagePath, onReset, preloadedRecom }: ResultsPageProps) {
  const [highlightedBookId, setHighlightedBookId] = useState<number | null>(null)
  const [recommendations, setRecommendations] = useState<any[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [finalImageUrl, setFinalImageUrl] = useState<string | null>(null)
  const [selectedBook, setSelectedBook] = useState<any | null>(null)
  const cardRefs = useRef<Record<number, HTMLDivElement | null>>({})
  const [showDebug, setShowDebug] = useState(false)
  const [debugStatus, setDebugStatus] = useState<Record<string, StepState>>({})
  const [debugSrc, setDebugSrc] = useState<Record<string, string | null>>({})

  const API_BASE = process.env.NEXT_PUBLIC_FASTAPI_URL || "http://localhost:8000"

  const debugFiles = [
    { key: 'masks_img', filename: 'masks_img.png', label: 'Mask Overlay' },
    { key: 'bbox_img', filename: 'bbox_img.png', label: 'BBox Image' },
    { key: 'segments_img', filename: 'segments_img.png', label: 'Segments Image' },
  ]

  // Read UID from localStorage (frontend generates/stores it). If not available, null.
  const clientUid = typeof window !== "undefined" ? window.localStorage.getItem("uid") : null

  const createSvgPlaceholder = (label: string) => {
    const w = 320
    const h = 240
    const svg = `<?xml version="1.0" encoding="UTF-8"?><svg xmlns='http://www.w3.org/2000/svg' width='${w}' height='${h}'><rect width='100%' height='100%' fill='#ffffff'/><text x='50%' y='50%' dominant-baseline='middle' text-anchor='middle' fill='#222' font-family='Arial, Helvetica, sans-serif' font-size='18'>${label}</text></svg>`
    return `data:image/svg+xml;utf8,${encodeURIComponent(svg)}`
  }

  const fetchDebugImages = async () => {
    const newSrc: Record<string, string | null> = {}
    const newStatus: Record<string, StepState> = {}
    debugFiles.forEach(d => {
      newSrc[d.key] = createSvgPlaceholder(d.label)
      newStatus[d.key] = 'loading'
    })
    setDebugSrc(newSrc)
    setDebugStatus(newStatus)

    for (const d of debugFiles) {
      try {
        // Prefer per-user debug filename if UID present (matches backend naming)
        const filenameWithUid = clientUid
          ? d.filename.replace(/\.(png|jpe?g)$/i, `_${clientUid}.$1`)
          : d.filename
        const res = await fetch(`${API_BASE}/api/image_upload/${filenameWithUid}`)
        if (!res.ok) throw new Error('Not found')
        const blob = await res.blob()
        newSrc[d.key] = URL.createObjectURL(blob)
        newStatus[d.key] = 'done'
      } catch {
        newSrc[d.key] = createSvgPlaceholder(d.label)
        newStatus[d.key] = 'error'
      }
      setDebugSrc({ ...newSrc })
      setDebugStatus({ ...newStatus })
    }
  }

  // Load recommendations
  useEffect(() => {
    let mounted = true
    const load = async () => {
      setLoading(true)
      setError(null)
      try {
        let recoms: any[] = []
        let finalUrl: string | null = null

        if (preloadedRecom && preloadedRecom.length > 0) {
          recoms = preloadedRecom
          finalUrl = imagePath || null
        } else {
          const res = await getRecommenderResults()
          if (!mounted) return
          if (!res.success) throw new Error(res.error || "Recommender call failed")
          const data = res.data || {}
          recoms = data.recom || []
          finalUrl = data.final_image_url || null
        }

        const mapped = recoms.map((r: any, idx: number) => ({
          id: idx + 1,
          title: r.title || "",
          author: r.authors || r.author || "",
          image: r.image_link || r.image || "",
          preview_link: r.preview_link || "",
          rating: r.rating || 0,
          confidence: `${Math.round((r.similarity_score || 0) * 100)}%`,
          description: r.description || "",
          _meta: r,
        }))

        setRecommendations(mapped)
        setFinalImageUrl(finalUrl)
      } catch (err: any) {
        console.error("Recommender error:", err)
        setError(String(err || "Unknown error"))
      } finally {
        setLoading(false)
      }
    }
    load()
    return () => { mounted = false }
  }, [])

  const handleCardClick = (id: number) => {
    setHighlightedBookId(id)
    const el = cardRefs.current[id]
    if (el && typeof el.scrollIntoView === "function") {
      el.scrollIntoView({ behavior: "smooth", block: "center" })
    }
  }

  useEffect(() => {
    if (showDebug) {
      fetchDebugImages()
    }
  }, [showDebug])

  /** --------------------------
   * Hover Magnifier Component
   * ------------------------- */
  const Magnifier = ({ src, zoom = 2 }: { src: string; zoom?: number }) => {
    const [active, setActive] = useState(false) // active only when Q pressed
    const [coords, setCoords] = useState({ x: 0, y: 0 })
    const imgRef = useRef<HTMLDivElement>(null)
    const [dimensions, setDimensions] = useState({ width: 0, height: 0 })

    // Track Q key
    useEffect(() => {
      const handleKeyDown = (e: KeyboardEvent) => {
        if (e.key.toLowerCase() === 'q') setActive(true)
      }
      const handleKeyUp = (e: KeyboardEvent) => {
        if (e.key.toLowerCase() === 'q') setActive(false)
      }
      window.addEventListener('keydown', handleKeyDown)
      window.addEventListener('keyup', handleKeyUp)
      return () => {
        window.removeEventListener('keydown', handleKeyDown)
        window.removeEventListener('keyup', handleKeyUp)
      }
    }, [])

    const handleMouseMove = (e: React.MouseEvent<HTMLDivElement>) => {
      if (!imgRef.current) return
      const rect = imgRef.current.getBoundingClientRect()
      setCoords({ x: e.clientX - rect.left, y: e.clientY - rect.top })
    }

    useEffect(() => {
      if (!imgRef.current) return
      const rect = imgRef.current.getBoundingClientRect()
      setDimensions({ width: rect.width, height: rect.height })
    }, [src])

    return (
      <div
        ref={imgRef}
        className="relative w-full"
        style={{ overflow: "hidden", cursor: active ? "crosshair" : "default" }}
        onMouseMove={handleMouseMove}
      >
        <img
          src={src}
          alt="Shelf analysis"
          className="w-full h-auto object-contain rounded"
          draggable={false}
        />
        {active && (
          <div
            className="absolute pointer-events-none border border-gray-300 rounded-full"
            style={{
              width: 150,
              height: 150,
              top: coords.y - 75,
              left: coords.x - 75,
              backgroundImage: `url(${src})`,
              backgroundRepeat: "no-repeat",
              backgroundSize: `${dimensions.width * zoom}px ${dimensions.height * zoom}px`,
              backgroundPosition: `-${coords.x * zoom - 75}px -${coords.y * zoom - 75}px`,
            }}
          />
        )}
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-background p-4">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <Button onClick={onReset} variant="ghost" className="text-muted-foreground hover:text-foreground">
            <ChevronLeft className="w-4 h-4 mr-2" />
            New Analysis
          </Button>
          <h1 className="text-3xl font-bold text-foreground flex items-center gap-2">
            <Zap className="w-8 h-8 text-accent" />
            Recommended Books
          </h1>
          <div className="w-24"></div>
        </div>

        {/* Image with Bounding Boxes + Magnifier */}
        <Card className="border border-border bg-card mb-8 overflow-hidden relative">
  <div className="p-6">
    <Magnifier src={finalImageUrl || imagePath || "/placeholder.svg"} zoom={2} />
    <p className="text-sm text-muted-foreground mt-4">
      {recommendations.length} book(s) detected on the shelf
      {highlightedBookId &&
        ` • Hovering over: ${recommendations.find((b) => b.id === highlightedBookId)?.title}`}
    </p>
  </div>

  {/* Hint text */}
  <span className="absolute bottom-3 right-4 text-xs text-muted-foreground italic select-none">
    Press <kbd className="px-1 py-0.5 bg-gray-200 rounded text-gray-700">Q</kbd> and hover to zoom
  </span>
</Card>

        {/* Debug Panel */}
        <div className="mt-4">
          <Card className="p-4">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-semibold">Debug</h3>
              <Button
                size="sm"
                variant={showDebug ? 'destructive' : 'outline'}
                onClick={() => setShowDebug((s) => !s)}
              >
                {showDebug ? 'Hide' : 'Show'}
              </Button>
            </div>

            {showDebug && (
              <div className="mt-3 flex gap-4 justify-between flex-wrap">
                {debugFiles.map((d) => (
                  <div key={d.key} className="flex flex-col items-center w-[32%]">
                    {/* Label */}
                    <span className="text-xs font-medium mb-1">{d.label}</span>

                    {/* Image Container */}
                    <div className="w-full h-[200px] flex items-center justify-center bg-gray-50 rounded border border-border overflow-hidden">
                      <Zoom>
                        {debugStatus[d.key] === 'loading' && !debugSrc[d.key] ? (
                          <Loader2 className="w-12 h-12 animate-spin text-muted-foreground" />
                        ) : (
                          <img
                            src={debugSrc[d.key] ?? createSvgPlaceholder(d.label)}
                            alt={d.label}
                            className="max-w-full max-h-full"
                            style={{ objectFit: 'contain', width: '100%', height: '100%' }}
                            draggable={false}
                          />
                        )}
                      </Zoom>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </Card>
        </div>

        {/* Book Recommendations */}
        <div className="mt-8">
          <h2 className="text-2xl font-bold text-foreground mb-6">
            Book Details & Recommendations
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {recommendations.map((book) => (
              <div
                key={book.id}
                ref={(el) => { cardRefs.current[book.id] = el }}
                onClick={() => handleCardClick(book.id)}
                onMouseEnter={() => setHighlightedBookId(book.id)}
                onMouseLeave={() => setHighlightedBookId(null)}
              >
                <BookRecommendationCard
                  book={book}
                  isHighlighted={highlightedBookId === book.id}
                  onDetails={(b) => setSelectedBook(b._meta || b)}
                />
              </div>
            ))}
          </div>
        </div>

        {/* Footer */}
        <div className="mt-12 pt-8 border-t border-border text-center">
          <p className="text-sm text-muted-foreground mb-4">Want to analyze another image?</p>
          <Button onClick={onReset} className="bg-primary hover:bg-primary/90 text-primary-foreground">
            Start New Analysis
          </Button>
        </div>
      </div>

      {selectedBook && (
        <BookDetailsModal book={selectedBook} onClose={() => setSelectedBook(null)} />
      )}
    </div>
  )
}
