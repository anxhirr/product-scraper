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
  const [isModalOpen, setIsModalOpen] = useState(false)

  const openModal = (result: ScrapeResult) => {
    setSelectedResult(result)
    setIsModalOpen(true)
  }

  const closeModal = () => {
    setIsModalOpen(false)
    setSelectedResult(null)
  }

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
      "Brand",
      "Category",
      "Description",
      "Specifications",
      "Images",
      "Source URL",
    ]

    // Transform products to rows
    const rows = successfulResults.map((result) => {
      const product = result.product!
      const barcode = getSpecValue(product.specifications, [
        "barcode",
        "Barcode",
        "BARCODE",
        "ean",
        "EAN",
        "upc",
        "UPC",
      ])
      const category = getSpecValue(product.specifications, [
        "category",
        "Category",
        "CATEGORY",
        "category_name",
        "Category Name",
      ])
      return [
        product.name || "",
        product.code || "",
        barcode,
        product.price || "",
        product.brand || "",
        category,
        product.description || "",
        product.specifications
          ? JSON.stringify(product.specifications)
          : "",
        product.images?.join(",") || "",
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

    // Add data rows
    exportData.rows.forEach((row) => {
      csvRows.push(row.map((cell) => escapeCsvValue(String(cell))).join(","))
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
                    {result.product?.price ? (
                      <span className="font-semibold text-primary">
                        {result.product.price}
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
