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
} from "lucide-react"
import type { ProductData } from "./product-scraper-form"
import ProductResults from "./product-results"

interface ScrapeResult {
  product?: ProductData
  error?: string
  status: "success" | "error" | "pending"
  originalData: {
    name?: string
    code?: string
    site: string
    brand?: string
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
                    <strong>Site:</strong> {selectedResult.originalData.site}
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
                  {selectedResult.originalData.brand && (
                    <p>
                      <strong>Brand:</strong> {selectedResult.originalData.brand}
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
