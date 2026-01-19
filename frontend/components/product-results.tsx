"use client"

import { useState } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Switch } from "@/components/ui/switch"
import { Label } from "@/components/ui/label"
import { useToast } from "@/hooks/use-toast"
import { ExternalLinkIcon, ImageIcon, FileTextIcon, ListIcon, DollarSignIcon, CopyIcon, CheckIcon, DownloadIcon } from "lucide-react"
import type { ProductData } from "./product-scraper-form"

interface ProductResultsProps {
  data: ProductData
}

export default function ProductResults({ data }: ProductResultsProps) {
  const { toast } = useToast()
  const [copiedDescription, setCopiedDescription] = useState(false)
  const [copiedSpecifications, setCopiedSpecifications] = useState(false)
  const [showAlbanian, setShowAlbanian] = useState(true) // Default to Albanian/translated

  // Get the current name (translated or original)
  const currentName = showAlbanian ? (data.name || data.nameOriginal) : (data.nameOriginal || data.name)

  // Get the current description (translated or original)
  const currentDescription = showAlbanian ? (data.description || data.descriptionOriginal) : (data.descriptionOriginal || data.description)

  // Get the current specifications (translated or original)
  const currentSpecifications = showAlbanian 
    ? (data.specifications || data.specificationsOriginal)
    : (data.specificationsOriginal || data.specifications)

  const copyToClipboard = async (text: string, type: "description" | "specifications") => {
    try {
      await navigator.clipboard.writeText(text)
      if (type === "description") {
        setCopiedDescription(true)
        setTimeout(() => setCopiedDescription(false), 2000)
      } else {
        setCopiedSpecifications(true)
        setTimeout(() => setCopiedSpecifications(false), 2000)
      }
      toast({
        title: "Copied!",
        description: `${type === "description" ? "Description" : "Specifications"} copied to clipboard`,
      })
    } catch (err) {
      toast({
        title: "Failed to copy",
        description: "Could not copy to clipboard",
      })
    }
  }

  const copyDescription = () => {
    if (currentDescription) {
      copyToClipboard(currentDescription, "description")
    }
  }

  const copySpecifications = () => {
    if (currentSpecifications) {
      copyToClipboard(formatSpecifications(currentSpecifications), "specifications")
    }
  }

  const formatSpecifications = (specs: Record<string, string>): string => {
    return Object.entries(specs)
      .map(([key, value]) => `${key}: ${value}`)
      .join("\n")
  }

  const downloadImage = async (imageUrl: string, filename: string) => {
    try {
      // Try fetching the image first
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
    } catch (err) {
      // Fallback: try using canvas to download (works for same-origin images)
      try {
        const img = new Image()
        img.crossOrigin = "anonymous"
        img.onload = () => {
          const canvas = document.createElement("canvas")
          canvas.width = img.width
          canvas.height = img.height
          const ctx = canvas.getContext("2d")
          if (ctx) {
            ctx.drawImage(img, 0, 0)
            canvas.toBlob((blob) => {
              if (blob) {
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
              } else {
                throw new Error("Failed to create blob")
              }
            })
          }
        }
        img.onerror = () => {
          // Last resort: open in new tab
          window.open(imageUrl, "_blank")
          toast({
            title: "Opened in new tab",
            description: "Please right-click and save the image",
          })
        }
        img.src = imageUrl
      } catch (fallbackErr) {
        // Last resort: open in new tab
        window.open(imageUrl, "_blank")
        toast({
          title: "Opened in new tab",
          description: "Please right-click and save the image",
        })
      }
    }
  }

  const downloadAllImages = async () => {
    if (!data.images || data.images.length === 0) return

    try {
      for (let i = 0; i < data.images.length; i++) {
        const imageUrl = data.images[i]
        const extension = imageUrl.split(".").pop()?.split("?")[0] || "jpg"
        const filename = `${(data.nameOriginal || data.name).replace(/[^a-z0-9]/gi, "_")}_${i + 1}.${extension}`
        
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
    return `${(data.nameOriginal || data.name).replace(/[^a-z0-9]/gi, "_")}_${index + 1}.${extension}`
  }
  // Check if we have both original and translated versions
  const hasBothVersions = (data.name && data.nameOriginal) ||
                          (data.description && data.descriptionOriginal) || 
                          (data.specifications && data.specificationsOriginal && 
                           Object.keys(data.specifications).length > 0 && 
                           Object.keys(data.specificationsOriginal).length > 0)

  return (
    <div className="space-y-6 animate-in fade-in-50 duration-500">
      <Card>
        <CardHeader>
          <div className="flex items-start justify-between">
            <div className="flex-1">
              <CardTitle className="text-2xl">{currentName}</CardTitle>
              <CardDescription className="mt-2">
                {data.brand ? `${data.brand} · ` : ""}{data.code}
              </CardDescription>
              {data.price && (
                <div className="mt-3 flex items-center gap-2">
                  <DollarSignIcon className="w-5 h-5 text-primary" />
                  <span className="text-2xl font-bold text-primary">{data.price}</span>
                </div>
              )}
              {hasBothVersions && (
                <div className="mt-4 flex items-center gap-3">
                  <Label htmlFor="language-toggle" className="text-sm text-muted-foreground cursor-pointer">
                    Original
                  </Label>
                  <Switch
                    id="language-toggle"
                    checked={showAlbanian}
                    onCheckedChange={setShowAlbanian}
                  />
                  <Label htmlFor="language-toggle" className="text-sm text-muted-foreground cursor-pointer">
                    Shqip (Albanian)
                  </Label>
                </div>
              )}
            </div>
            {data.sourceUrl && (
              <a
                href={data.sourceUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="text-sm text-muted-foreground hover:text-foreground flex items-center gap-1 ml-4"
              >
                View Source
                <ExternalLinkIcon className="w-4 h-4" />
              </a>
            )}
          </div>
        </CardHeader>
      </Card>

      {currentDescription && (
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
            <p className="text-foreground leading-relaxed">{currentDescription}</p>
          </CardContent>
        </Card>
      )}

      {currentSpecifications && Object.keys(currentSpecifications).length > 0 && (
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
            <dl className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {Object.entries(currentSpecifications).map(([key, value]) => (
                <div key={key} className="space-y-1">
                  <dt className="text-sm font-medium text-muted-foreground">{key}</dt>
                  <dd className="text-sm text-foreground">{value}</dd>
                </div>
              ))}
            </dl>
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
                    alt={`${currentName} - Image ${index + 1}`}
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
