"use client"

import { useState } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { useToast } from "@/hooks/use-toast"
import { ExternalLinkIcon, ImageIcon, FileTextIcon, ListIcon, CopyIcon, CheckIcon, DownloadIcon } from "lucide-react"
import type { ProductData } from "./product-scraper-form"

interface ProductResultsProps {
  data: ProductData
}

export default function ProductResults({ data }: ProductResultsProps) {
  const { toast } = useToast()
  const [copiedName, setCopiedName] = useState(false)
  const [copiedDescription, setCopiedDescription] = useState(false)
  const [copiedSpecifications, setCopiedSpecifications] = useState(false)

  const copyToClipboard = async (text: string, type: "name" | "description" | "specifications") => {
    try {
      await navigator.clipboard.writeText(text)
      if (type === "name") {
        setCopiedName(true)
        setTimeout(() => setCopiedName(false), 2000)
      } else if (type === "description") {
        setCopiedDescription(true)
        setTimeout(() => setCopiedDescription(false), 2000)
      } else {
        setCopiedSpecifications(true)
        setTimeout(() => setCopiedSpecifications(false), 2000)
      }
      toast({
        title: "Copied!",
        description: `${type === "name" ? "Name" : type === "description" ? "Description" : "Specifications"} copied to clipboard`,
      })
    } catch (err) {
      toast({
        title: "Failed to copy",
        description: "Could not copy to clipboard",
      })
    }
  }

  const copyName = () => {
    if (data.name) {
      copyToClipboard(data.name, "name")
    }
  }

  const copyDescription = () => {
    if (data.description) {
      copyToClipboard(data.description, "description")
    }
  }

  const copySpecifications = () => {
    if (data.specifications) {
      copyToClipboard(formatSpecifications(data.specifications), "specifications")
    }
  }

  const formatSpecifications = (specs: Record<string, string>): string => {
    return Object.entries(specs)
      .map(([key, value]) => `${key}: ${value}`)
      .join("\n")
  }

  const downloadImage = async (imageUrl: string, filename: string) => {
    const response = await fetch(imageUrl, { mode: "cors" })
    if (!response.ok) {
      throw new Error("Failed to fetch image")
    }
    const blob = await response.blob()
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement("a")
    link.href = url
    link.download = filename
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    window.URL.revokeObjectURL(url)
    toast({
      title: "Downloaded!",
      description: `Image saved as ${filename}`,
    })
  }

  const downloadAllImages = async () => {
    if (!data.images || data.images.length === 0) return

    try {
      for (let i = 0; i < data.images.length; i++) {
        const imageUrl = data.images[i]
        const extension = imageUrl.split(".").pop()?.split("?")[0] || "jpg"
        const filename = `${data.name.replace(/[^a-z0-9]/gi, "_")}_${i + 1}.${extension}`
        
        // Add a small delay between downloads to avoid overwhelming the browser
        if (i > 0) {
          await new Promise((resolve) => setTimeout(resolve, 300))
        }
        
        await downloadImage(imageUrl, filename)
      }
      toast({
        title: "All images downloaded!",
        description: `Downloaded ${data.images.length} image(s)`,
      })
    } catch (err) {
      toast({
        title: "Download failed",
        description: "Some images could not be downloaded",
      })
    }
  }

  const getImageFilename = (imageUrl: string, index: number): string => {
    const extension = imageUrl.split(".").pop()?.split("?")[0] || "jpg"
    return `${data.name.replace(/[^a-z0-9]/gi, "_")}_${index + 1}.${extension}`
  }

  return (
    <div className="space-y-6 animate-in fade-in-50 duration-500">
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between mb-2">
            <CardTitle className="text-2xl">{data.name}</CardTitle>
            <Button
              variant="outline"
              size="sm"
              onClick={copyName}
              className="gap-2"
            >
              {copiedName ? (
                <>
                  <CheckIcon className="w-4 h-4" />
                  Copied
                </>
              ) : (
                <>
                  <CopyIcon className="w-4 h-4" />
                  Copy
                </>
              )}
            </Button>
          </div>
          <CardDescription className="mt-2">
            {data.brand ? `${data.brand} · ` : ""}{data.code}
          </CardDescription>
          {data.price && (
            <div className="mt-3 flex items-center gap-2">
              <span className="text-2xl font-bold text-primary">
                {data.price.includes("ALL") || data.price.includes("Lek") || data.price.includes("lek")
                  ? data.price
                  : `${data.price} ALL`}
              </span>
            </div>
          )}
        </CardHeader>
        {data.sourceUrl && (
          <CardContent>
            <Button
              variant="outline"
              size="sm"
              asChild
              className="gap-2"
            >
              <a
                href={data.sourceUrl}
                target="_blank"
                rel="noopener noreferrer"
              >
                View Source
                <ExternalLinkIcon className="w-4 h-4" />
              </a>
            </Button>
          </CardContent>
        )}
      </Card>

      {data.description && (
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle className="flex items-center gap-2">
                <FileTextIcon className="w-5 h-5" />
                Description
              </CardTitle>
              <Button
                variant="outline"
                size="sm"
                onClick={copyDescription}
                className="gap-2"
              >
                {copiedDescription ? (
                  <>
                    <CheckIcon className="w-4 h-4" />
                    Copied
                  </>
                ) : (
                  <>
                    <CopyIcon className="w-4 h-4" />
                    Copy
                  </>
                )}
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            <p className="text-foreground leading-relaxed">{data.description}</p>
          </CardContent>
        </Card>
      )}

      {data.specifications && Object.keys(data.specifications).length > 0 && (
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle className="flex items-center gap-2">
                <ListIcon className="w-5 h-5" />
                Specifications
              </CardTitle>
              <Button
                variant="outline"
                size="sm"
                onClick={copySpecifications}
                className="gap-2"
              >
                {copiedSpecifications ? (
                  <>
                    <CheckIcon className="w-4 h-4" />
                    Copied
                  </>
                ) : (
                  <>
                    <CopyIcon className="w-4 h-4" />
                    Copy
                  </>
                )}
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            <p className="text-foreground leading-relaxed whitespace-pre-line">
              {formatSpecifications(data.specifications)}
            </p>
          </CardContent>
        </Card>
      )}

      {data.images && data.images.length > 0 && (
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle className="flex items-center gap-2">
                <ImageIcon className="w-5 h-5" />
                Product Images
              </CardTitle>
              <Button
                variant="outline"
                size="sm"
                onClick={downloadAllImages}
                className="gap-2"
              >
                <DownloadIcon className="w-4 h-4" />
                Download All
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
              {data.images.map((image, index) => (
                <div key={index} className="relative group aspect-square rounded-lg overflow-hidden border bg-muted">
                  <img
                    src={image || "/placeholder.svg"}
                    alt={`${data.name} - Image ${index + 1}`}
                    className="w-full h-full object-cover hover:scale-105 transition-transform duration-300"
                  />
                  <div className="absolute inset-0 bg-black/50 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
                    <Button
                      variant="secondary"
                      size="sm"
                      onClick={() => downloadImage(image, getImageFilename(image, index + 1))}
                      className="gap-2"
                    >
                      <DownloadIcon className="w-4 h-4" />
                      Download
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
