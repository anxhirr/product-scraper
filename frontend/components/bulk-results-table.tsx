"use client"

import { useState } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet"
import {
  CheckCircleIcon,
  XCircleIcon,
  ClockIcon,
  ExternalLinkIcon,
  EyeIcon,
  DownloadIcon,
  ChevronLeftIcon,
  ChevronRightIcon,
} from "lucide-react"
import { useToast } from "@/hooks/use-toast"
import type { ProductData } from "./product-scraper-form"
import ProductResults from "./product-results"

interface ScrapeResult {
  product?: ProductData
  error?: string
  status: "success" | "error" | "pending"
  originalData: {
    name?: string
    code?: string
    brand: string
    category?: string
    barcode?: string
    price?: string
    quantity?: string
  }
}

interface BulkResultsTableProps {
  results: ScrapeResult[]
  isScraping: boolean
}

export default function BulkResultsTable({
  results,
  isScraping,
}: BulkResultsTableProps) {
  const { toast } = useToast()
  const [selectedResult, setSelectedResult] = useState<ScrapeResult | null>(null)
  const [selectedIndex, setSelectedIndex] = useState<number>(-1)
  const [isModalOpen, setIsModalOpen] = useState(false)

  // Get all successful results for navigation
  const successfulResults = results.filter((r) => r.status === "success" && r.product)

  const openModal = (result: ScrapeResult) => {
    setSelectedResult(result)
    // Find the index of this result in the results array
    const index = results.findIndex((r) => r === result)
    setSelectedIndex(index)
    setIsModalOpen(true)
  }

  const closeModal = () => {
    setIsModalOpen(false)
    setSelectedResult(null)
    setSelectedIndex(-1)
  }

  const navigateToPrevious = () => {
    if (selectedIndex > 0) {
      const newIndex = selectedIndex - 1
      setSelectedIndex(newIndex)
      setSelectedResult(results[newIndex])
    }
  }

  const navigateToNext = () => {
    if (selectedIndex < results.length - 1) {
      const newIndex = selectedIndex + 1
      setSelectedIndex(newIndex)
      setSelectedResult(results[newIndex])
    }
  }

  const canNavigatePrevious = selectedIndex > 0
  const canNavigateNext = selectedIndex < results.length - 1

  const successCount = results.filter((r) => r.status === "success").length
  const errorCount = results.filter((r) => r.status === "error").length
  const pendingCount = results.filter((r) => r.status === "pending").length

  const getStatusBadge = (status: ScrapeResult["status"]) => {
    switch (status) {
      case "success":
        return (
          <Badge variant="default" className="bg-green-500">
            <CheckCircleIcon className="w-3 h-3 mr-1" />
            Success
          </Badge>
        )
      case "error":
        return (
          <Badge variant="destructive">
            <XCircleIcon className="w-3 h-3 mr-1" />
            Error
          </Badge>
        )
      case "pending":
        return (
          <Badge variant="secondary">
            <ClockIcon className="w-3 h-3 mr-1" />
            Pending
          </Badge>
        )
    }
  }

  // Helper function to escape CSV values
  const escapeCsvValue = (value: string): string => {
    if (!value) return ""
    // If value contains comma, quote, or newline, wrap in quotes and escape quotes
    if (value.includes(",") || value.includes('"') || value.includes("\n")) {
      return `"${value.replace(/"/g, '""')}"`
    }
    return value
  }

  // Helper function to format barcode for CSV (prevents Excel from converting to scientific notation)
  // We preserve the original barcode value and quote it - no conversion needed
  const formatBarcodeForCsv = (barcode: string): string => {
    if (!barcode) return ""
    // Just trim and return - the quoting in escapeCsvValueWithBarcode will handle Excel formatting
    return barcode.trim()
  }
  
  // Helper function to escape CSV values, with special handling for barcodes
  const escapeCsvValueWithBarcode = (value: string, isBarcode: boolean = false): string => {
    if (!value) return ""
    
    // Always quote barcodes to force Excel to treat as text
    if (isBarcode) {
      return `"${value.replace(/"/g, '""')}"`
    }
    
    // If value contains comma, quote, or newline, wrap in quotes and escape quotes
    if (value.includes(",") || value.includes('"') || value.includes("\n")) {
      return `"${value.replace(/"/g, '""')}"`
    }
    return value
  }

  // Helper function to get export data
  const getExportData = () => {
    // Filter to only successful results with valid product data
    const successfulResults = results.filter(
      (r) => r.status === "success" && r.product
    )

    if (successfulResults.length === 0) {
      return null
    }

    // Helper function to extract value from specifications
    const getSpecValue = (
      specs: Record<string, string> | undefined,
      keys: string[]
    ): string => {
      if (!specs) return ""
      for (const key of keys) {
        // Try exact match first
        if (specs[key]) return specs[key]
        // Try case-insensitive match
        const foundKey = Object.keys(specs).find(
          (k) => k.toLowerCase() === key.toLowerCase()
        )
        if (foundKey) return specs[foundKey]
      }
      return ""
    }

    // Define headers
    const headers = [
      "Name",
      "Code",
      "Barcode",
      "Price",
      "Quantity",
      "Brand",
      "Category",
      "Description",
      "Specifications",
      "Images",
      "Primary Image",
      "Source URL",
    ]

    // Transform products to rows
    const rows = successfulResults.map((result) => {
      const product = result.product!
      // Prioritize Excel values over scraped values
      const barcode = result.originalData.barcode || getSpecValue(product.specifications, [
        "barcode",
        "Barcode",
        "BARCODE",
        "ean",
        "EAN",
        "upc",
        "UPC",
      ])
      const category = result.originalData.category || getSpecValue(product.specifications, [
        "category",
        "Category",
        "CATEGORY",
        "category_name",
        "Category Name",
      ])
      const quantity = result.originalData.quantity || getSpecValue(product.specifications, [
        "quantity",
        "Quantity",
        "QUANTITY",
        "qty",
        "Qty",
        "stock",
        "Stock",
      ])
      const price = result.originalData.price || product.price || ""
      return [
        product.name || "",
        product.code || "",
        formatBarcodeForCsv(barcode),
        price,
        quantity,
        product.brand || "",
        category,
        product.description || "",
        product.specifications
          ? JSON.stringify(product.specifications)
          : "",
        product.images?.join(",") || "",
        product.primaryImage || "",
        product.sourceUrl || "",
      ]
    })

    return { headers, rows, count: successfulResults.length }
  }

  const exportToCsv = () => {
    const exportData = getExportData()

    if (!exportData) {
      toast({
        title: "No data to export",
        description: "There are no successful scraping results to export",
        variant: "destructive",
      })
      return
    }

    // Create CSV content
    const csvRows: string[] = []

    // Add headers
    csvRows.push(exportData.headers.map(escapeCsvValue).join(","))

    // Add data rows - barcode is at index 2 (Name=0, Code=1, Barcode=2)
    const BARCODE_INDEX = 2
    exportData.rows.forEach((row) => {
      csvRows.push(
        row
          .map((cell, index) =>
            index === BARCODE_INDEX
              ? escapeCsvValueWithBarcode(String(cell), true)
              : escapeCsvValue(String(cell))
          )
          .join(",")
      )
    })

    const csvContent = csvRows.join("\n")

    // Create blob and trigger download
    const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" })
    const url = URL.createObjectURL(blob)

    // Generate filename with timestamp
    const now = new Date()
    const timestamp = now
      .toISOString()
      .replace(/T/, "-")
      .replace(/\..+/, "")
      .replace(/:/g, "-")
    const filename = `scraping-results-${timestamp}.csv`

    // Create download link and trigger
    const link = document.createElement("a")
    link.href = url
    link.download = filename
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    URL.revokeObjectURL(url)

    toast({
      title: "Export successful",
      description: `Exported ${exportData.count} product(s) to ${filename}`,
    })
  }


  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle>Scraping Results</CardTitle>
            <CardDescription className="mt-2">
              {successCount} successful, {errorCount} errors
              {pendingCount > 0 && `, ${pendingCount} pending`}
            </CardDescription>
          </div>
          {successCount > 0 && (
            <Button
              variant="outline"
              size="sm"
              onClick={exportToCsv}
              className="gap-2"
            >
              <DownloadIcon className="w-4 h-4" />
              Export to CSV
            </Button>
          )}
        </div>
      </CardHeader>
      <CardContent>
        <div className="rounded-md border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Name</TableHead>
                <TableHead>Code</TableHead>
                <TableHead>Price</TableHead>
                <TableHead>Brand</TableHead>
                <TableHead>Status</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {results.map((result, index) => (
                <TableRow key={index}>
                  <TableCell className="font-medium">
                    {result.product?.name ||
                      result.product?.nameOriginal ||
                      result.originalData.name ||
                      "-"}
                  </TableCell>
                  <TableCell>
                    {result.product?.code || result.originalData.code || "-"}
                  </TableCell>
                  <TableCell>
                    {result.originalData.price || result.product?.price ? (
                      <span className="font-semibold text-primary">
                        {(() => {
                          const price = result.originalData.price || result.product?.price || ""
                          return price.includes("ALL") || price.includes("Lek") || price.includes("lek")
                            ? price
                            : `${price} ALL`
                        })()}
                      </span>
                    ) : (
                      "-"
                    )}
                  </TableCell>
                  <TableCell>
                    {result.product?.brand ||
                      result.originalData.brand ||
                      "-"}
                  </TableCell>
                  <TableCell>{getStatusBadge(result.status)}</TableCell>
                  <TableCell className="text-right">
                    <div className="flex items-center justify-end gap-2">
                      {result.status === "success" && result.product && (
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => openModal(result)}
                          className="gap-2"
                        >
                          <EyeIcon className="w-3 h-3" />
                          View
                        </Button>
                      )}
                      {result.status === "error" && (
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => openModal(result)}
                          className="gap-2"
                        >
                          <EyeIcon className="w-3 h-3" />
                          View Error
                        </Button>
                      )}
                      {result.product?.sourceUrl && (
                        <Button
                          variant="ghost"
                          size="sm"
                          asChild
                          className="gap-2"
                        >
                          <a
                            href={result.product.sourceUrl}
                            target="_blank"
                            rel="noopener noreferrer"
                          >
                            <ExternalLinkIcon className="w-3 h-3" />
                          </a>
                        </Button>
                      )}
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      </CardContent>

      {/* Product Details Sheet */}
      <Sheet open={isModalOpen} onOpenChange={setIsModalOpen}>
        <SheetContent side="right" className="w-full sm:max-w-2xl overflow-y-auto p-6">
          <SheetHeader className="pb-4">
            <div className="flex items-center justify-between gap-4">
              <div className="flex-1 min-w-0">
                <SheetTitle>
                  {selectedResult?.status === "success" && selectedResult?.product
                    ? selectedResult.product.name ||
                      selectedResult.product.nameOriginal ||
                      "Product Details"
                    : "Error Details"}
                </SheetTitle>
                <SheetDescription>
                  {selectedResult?.status === "success"
                    ? "View full product information"
                    : "View error information"}
                </SheetDescription>
              </div>
              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  size="icon"
                  onClick={navigateToPrevious}
                  disabled={!canNavigatePrevious}
                  className="shrink-0"
                >
                  <ChevronLeftIcon className="w-4 h-4" />
                  <span className="sr-only">Previous product</span>
                </Button>
                <div className="text-sm text-muted-foreground min-w-[60px] text-center">
                  {selectedIndex >= 0 && results.length > 0
                    ? `${selectedIndex + 1} / ${results.length}`
                    : ""}
                </div>
                <Button
                  variant="outline"
                  size="icon"
                  onClick={navigateToNext}
                  disabled={!canNavigateNext}
                  className="shrink-0"
                >
                  <ChevronRightIcon className="w-4 h-4" />
                  <span className="sr-only">Next product</span>
                </Button>
              </div>
            </div>
          </SheetHeader>

          <div className="px-2">
            {selectedResult?.status === "error" && (
              <div className="p-4 bg-destructive/10 border border-destructive/20 rounded-md">
                <p className="text-sm font-medium text-destructive mb-2">
                  Error: {selectedResult.error || "Unknown error"}
                </p>
                <div className="text-xs text-muted-foreground space-y-1">
                  <p>
                    <strong>Brand:</strong> {selectedResult.originalData.brand}
                  </p>
                  {selectedResult.originalData.name && (
                    <p>
                      <strong>Name:</strong> {selectedResult.originalData.name}
                    </p>
                  )}
                  {selectedResult.originalData.code && (
                    <p>
                      <strong>Code:</strong> {selectedResult.originalData.code}
                    </p>
                  )}
                </div>
              </div>
            )}

            {selectedResult?.status === "success" &&
              selectedResult?.product && (
                <ProductResults data={selectedResult.product} />
              )}

            {selectedResult?.status === "pending" && (
              <div className="p-4 bg-muted border rounded-md">
                <p className="text-sm text-muted-foreground">
                  Scraping in progress...
                </p>
              </div>
            )}
          </div>
        </SheetContent>
      </Sheet>
    </Card>
  )
}
