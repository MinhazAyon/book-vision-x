"use client"

import React from "react"
import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"

interface Props {
  book: any
  onClose: () => void
}

export default function BookDetailsModal({ book, onClose }: Props) {
  if (!book) return null

  // filter out fields we don't want to show in the details list
  const metadata = { ...book }
  // remove internal fields and large links/coords from the displayed metadata
  delete metadata.serial_no
  delete metadata.positions
  delete metadata.coord
  delete metadata.image_link
  delete metadata.preview_link
  delete metadata.image

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <div className="max-w-4xl w-full max-h-[85vh]">
        <Card className="p-6 overflow-auto max-h-[85vh]">
          <div className="flex justify-end mb-4">
            <Button variant="ghost" onClick={onClose} className="text-sm">
              Close
            </Button>
          </div>
          <div className="flex flex-col md:flex-row gap-6">
            <div className="flex-shrink-0 flex items-start">
              <img
                src={book.image_link || book.image || book.preview_link || "/placeholder.svg"}
                alt={book.title}
                className="max-w-xs w-full h-auto object-contain rounded"
              />
            </div>

            <div className="flex-1 min-w-0">
              <h2 className="text-2xl font-semibold break-words">{book.title}</h2>
              <p className="text-sm text-muted-foreground mb-4">by {book.authors || book.author}</p>

              <div className="w-full mt-2 grid grid-cols-1 gap-3 text-sm overflow-auto max-h-[55vh] pr-2">
                {Object.entries(metadata).map(([k, v]) => (
                  <div key={k} className="flex gap-3">
                    <div className="font-semibold w-36 text-muted-foreground flex-shrink-0">{k.replace(/_/g, " ")}</div>
                    <div className="flex-1 break-words whitespace-pre-wrap">{Array.isArray(v) ? JSON.stringify(v) : String(v)}</div>
                  </div>
                ))}
              </div>

              <div className="mt-6">
                <Button onClick={onClose} className="bg-primary hover:bg-primary/90 text-primary-foreground">
                  Close
                </Button>
              </div>
            </div>
          </div>
        </Card>
      </div>
    </div>
  )
}
