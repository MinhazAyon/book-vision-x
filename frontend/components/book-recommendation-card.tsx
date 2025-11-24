"use client"

import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { Eye, BookOpen, Star } from "lucide-react" 

interface Book {
  id: number
  title: string
  author: string
  image: string
  preview_link: string
  rating: number
  confidence: string
  description: string
  boundingBox?: { x: number; y: number; width: number; height: number }
}

interface BookRecommendationCardProps {
  book: Book
  isHighlighted?: boolean
  onDetails?: (book: any) => void
}
export default function BookRecommendationCard({ book, isHighlighted, onDetails }: BookRecommendationCardProps) {
  // Use _meta fields when available (recommender returns full metadata there)
  const meta: any = (book as any)._meta || book
  return (
    <Card
      className={`border transition-all overflow-hidden flex flex-col h-full ${
        isHighlighted
          ? "border-primary/60 bg-primary/5 shadow-sm shadow-primary/20"
          : "border-border/50 bg-card hover:border-primary/50 hover:shadow-sm"
      }`}
    >
      {/* Book Image */}
      <div className="relative overflow-hidden bg-muted">
        <img
          src={book.image || "/placeholder.svg?height=200&width=150&query=book-cover"}
          alt={book.title}
          className={`w-full h-48 object-cover transition-transform duration-300 ${
            isHighlighted ? "scale-105" : "group-hover:scale-105"
          }`}
        />
        <div
          className={`absolute top-3 right-3 px-2.5 py-1 rounded-md text-xs font-semibold transition-all ${
            isHighlighted ? "bg-primary text-primary-foreground" : "bg-primary/90 text-primary-foreground"
          }`}
        >
          {book.confidence}
        </div>
      </div>

      {/* Card Content */}
      <div className="p-5 flex flex-col flex-1">
  <h3 className="text-base font-semibold text-foreground mb-1 line-clamp-2">{book.title || meta.title}</h3>
  <p className="text-xs text-muted-foreground mb-3">by {book.author || meta.authors || meta.author}</p>

        {/* Rating */}
        <div className="flex items-center gap-1.5 mb-3"> 
          <Star className="w-4 h-4 fill-accent text-accent" />
          <span className="text-sm font-semibold text-foreground">{book.rating ?? meta.google_rating ?? ""}</span>
        </div>

        {/* Description */}
  <p className="text-xs text-muted-foreground mb-4 line-clamp-3 flex-grow leading-relaxed">{book.description || meta.description}</p>

        {/* Action Buttons */}
        <div className="flex gap-2 mt-auto">
            <Button
            size="sm"
            className="flex-1 bg-primary text-primary-foreground hover:bg-primary/90 text-xs font-medium h-9"
            onClick={() => window.open(book.preview_link, "_blank")}
          >
            <Eye className="w-3.5 h-3.5 mr-1.5" />
            Preview
          </Button>
          <Button
            size="sm"
            variant="outline"
            className="flex-1 text-xs font-medium h-9 bg-transparent"
            onClick={() => onDetails && onDetails(book)}
          >
            <BookOpen className="w-3.5 h-3.5 mr-1.5" />
            Details
          </Button>
        </div>
      </div>
    </Card>
  )
}
