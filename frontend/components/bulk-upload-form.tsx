"use client"

import type React from "react"
import { useState, useCallback, useEffect, useRef } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Progress } from "@/components/ui/progress"
import { useToast } from "@/hooks/use-toast"
import { UploadIcon, FileSpreadsheetIcon, PlayIcon } from "lucide-react"
import * as XLSX from "xlsx"
import ColumnMapper from "./column-mapper"
import BulkResultsTable from "./bulk-results-table"
import type { ProductData } from "./product-scraper-form"
import { usePolling } from "@/hooks/use-polling"

interface ExcelRow {
  [key: string]: string | number | null
}

interface MappedProduct {
  name?: string
  code?: string
  brand: string
  category?: string
  barcode?: string
  price?: string
  quantity?: string
}

interface ScrapeResult {
  product?: ProductData
  error?: string
  status: "success" | "error" | "pending"
  originalData: MappedProduct
  originalExcelRow?: ExcelRow // Full original Excel row data
}

export default function BulkUploadForm() {
  const { toast } = useToast()
  const [excelData, setExcelData] = useState<ExcelRow[]>([])
  const [columns, setColumns] = useState<string[]>([])
  const [columnMapping, setColumnMapping] = useState<{
    name?: string
    code?: string
    brand?: string
    category?: string
    barcode?: string
    price?: string
    quantity?: string
  }>({})
  const [batchSize, setBatchSize] = useState(200)
  const [batchDelay, setBatchDelay] = useState(1000)
  const [navigationDelay, setNavigationDelay] = useState(1000)
  const [isScraping, setIsScraping] = useState(false)
  const [scrapeProgress, setScrapeProgress] = useState(0)
  const [results, setResults] = useState<ScrapeResult[]>([])
  const [file, setFile] = useState<File | null>(null)
  const [jobId, setJobId] = useState<string | null>(null)
  const [validProducts, setValidProducts] = useState<MappedProduct[]>([])
  const [isRetryingAll, setIsRetryingAll] = useState(false)
  const [retryingIndices, setRetryingIndices] = useState<Set<number>>(new Set())

  // Auto-detect column mappings based on column names
  const autoDetectMappings = useCallback((columnNames: string[]) => {
    const mapping: {
      name?: string
      code?: string
      brand?: string
      category?: string
      barcode?: string
      price?: string
      quantity?: string
    } = {}

    const normalizedColumns = columnNames.map((col) => col.toLowerCase().trim())

    // Patterns for product name (English and Albanian)
    const namePatterns = [
      /^name$/i,
      /^product\s*name$/i,
      /^title$/i,
      /^product\s*title$/i,
      /^item\s*name$/i,
      /^product$/i,
      /^item$/i,
      /^description$/i,
      // Albanian patterns
      /^emri$/i,
      /^emri\s*i\s*produktit$/i,
      /^titulli$/i,
      /^titulli\s*i\s*produktit$/i,
      /^përshkrimi$/i,
      /^përshkrim$/i,
      /^pershkrimi$/i,
      /^pershkrim$/i,
      /^produkti$/i,
      /^artikulli$/i,
    ]

    // Patterns for product code/SKU (English and Albanian)
    const codePatterns = [
      /^code$/i,
      /^sku$/i,
      /^product\s*code$/i,
      /^product\s*sku$/i,
      /^item\s*code$/i,
      /^item\s*sku$/i,
      /^model$/i,
      /^model\s*number$/i,
      /^part\s*number$/i,
      /^id$/i,
      /^product\s*id$/i,
      // Albanian patterns
      /^kodi$/i,
      /^kodi\s*i\s*produktit$/i,
      /^kodi\s*artikullit$/i,
      /^kodi\s*i\s*artikullit$/i,
      /^modeli$/i,
      /^numri\s*i\s*modelit$/i,
      /^identifikuesi$/i,
      /^identifikimi$/i,
    ]

    // Patterns for brand (English and Albanian)
    const brandPatterns = [
      /^brand$/i,
      /^manufacturer$/i,
      /^maker$/i,
      /^company$/i,
      /^vendor$/i,
      /^supplier$/i,
      // Albanian patterns
      /^marka$/i,
      /^prodhuesi$/i,
      /^kompania$/i,
      /^furnizuesi$/i,
      /^blerësi$/i,
      /^shitësi$/i,
      /^marca$/i, // Alternative spelling
    ]

    // Patterns for price (English and Albanian)
    const pricePatterns = [
      /^price$/i,
      /^cost$/i,
      /^amount$/i,
      /^value$/i,
      /^prize$/i,
      /^pricing$/i,
      // Albanian patterns
      /^çmimi$/i,
      /^cmimi$/i,
      /^çmim$/i,
      /^cmim$/i,
      /^vlera$/i,
    ]

    // Patterns for barcode (English and Albanian)
    const barcodePatterns = [
      /^barcode$/i,
      /^bar\s*code$/i,
      /^ean$/i,
      /^upc$/i,
      /^gtin$/i,
      /^product\s*code$/i,
      // Albanian patterns
      /^barkod$/i,
      /^barkodi$/i,
      /^bar\s*kod$/i,
      /^kodi\s*i\s*barkodit$/i,
    ]

    // Patterns for category (English and Albanian)
    const categoryPatterns = [
      /^category$/i,
      /^cat$/i,
      /^categories$/i,
      /^type$/i,
      /^product\s*type$/i,
      /^product\s*category$/i,
      // Albanian patterns
      /^kategoria$/i,
      /^kategori$/i,
      /^kategoritë$/i,
      /^lloji$/i,
      /^lloji\s*i\s*produktit$/i,
    ]

    // Patterns for quantity (English and Albanian)
    const quantityPatterns = [
      /^quantity$/i,
      /^qty$/i,
      /^qty\.$/i,
      /^stock$/i,
      /^inventory$/i,
      /^available$/i,
      /^available\s*quantity$/i,
      /^stock\s*quantity$/i,
      // Albanian patterns
      /^sasia$/i,
      /^sasi$/i,
      /^stoku$/i,
      /^stok$/i,
      /^disponueshme$/i,
      /^sasia\s*e\s*disponueshme$/i,
    ]

    // Find matches
    for (let i = 0; i < columnNames.length; i++) {
      const col = columnNames[i]
      const normalized = normalizedColumns[i]

      // Check for name
      if (!mapping.name) {
        for (const pattern of namePatterns) {
          if (pattern.test(normalized)) {
            mapping.name = col
            break
          }
        }
      }

      // Check for code
      if (!mapping.code) {
        for (const pattern of codePatterns) {
          if (pattern.test(normalized)) {
            mapping.code = col
            break
          }
        }
      }

      // Check for brand
      if (!mapping.brand) {
        for (const pattern of brandPatterns) {
          if (pattern.test(normalized)) {
            mapping.brand = col
            break
          }
        }
      }

      // Check for price
      if (!mapping.price) {
        for (const pattern of pricePatterns) {
          if (pattern.test(normalized)) {
            mapping.price = col
            break
          }
        }
      }

      // Check for barcode
      if (!mapping.barcode) {
        for (const pattern of barcodePatterns) {
          if (pattern.test(normalized)) {
            mapping.barcode = col
            break
          }
        }
      }

      // Check for category
      if (!mapping.category) {
        for (const pattern of categoryPatterns) {
          if (pattern.test(normalized)) {
            mapping.category = col
            break
          }
        }
      }

      // Check for quantity
      if (!mapping.quantity) {
        for (const pattern of quantityPatterns) {
          if (pattern.test(normalized)) {
            mapping.quantity = col
            break
          }
        }
      }
    }

    return mapping
  }, [])

  const handleFileUpload = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const uploadedFile = e.target.files?.[0]
    if (!uploadedFile) return

    // Validate file type
    const validTypes = [
      "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", // .xlsx
      "application/vnd.ms-excel", // .xls
    ]
    if (!validTypes.includes(uploadedFile.type) && !uploadedFile.name.match(/\.(xlsx|xls)$/i)) {
      toast({
        title: "Invalid file type",
        description: "Please upload an Excel file (.xlsx or .xls)",
        variant: "destructive",
      })
      return
    }

    setFile(uploadedFile)

    const reader = new FileReader()
    reader.onload = (event) => {
      try {
        const data = event.target?.result
        if (!data) return

        const workbook = XLSX.read(data, { type: "binary" })
        const firstSheetName = workbook.SheetNames[0]
        const worksheet = workbook.Sheets[firstSheetName]
        // Use raw: true to preserve cell values, then format barcodes as text
        const jsonData: ExcelRow[] = XLSX.utils.sheet_to_json(worksheet, {
          raw: true,
          defval: null,
        })
        
        // Helper function to convert number to string without scientific notation
        const numberToString = (num: number): string => {
          if (num % 1 === 0) {
            // Integer - use BigInt for precision with large numbers
            return BigInt(num).toString()
          }
          // Float - convert normally
          return String(num)
        }
        
        // Convert numeric barcodes to full string representation (no scientific notation)
        // This handles cases where Excel stores barcodes as numbers
        jsonData.forEach((row) => {
          Object.keys(row).forEach((key) => {
            const value = row[key]
            if (typeof value === 'number') {
              // Convert numbers to string without scientific notation
              row[key] = numberToString(value)
            }
          })
        })

        if (jsonData.length === 0) {
          toast({
            title: "Empty file",
            description: "The Excel file appears to be empty",
            variant: "destructive",
          })
          return
        }

        // Load all rows from Excel file
        const totalRows = jsonData.length

        // Extract column names
        const columnNames = Object.keys(jsonData[0])
        setColumns(columnNames)
        setExcelData(jsonData)

        // Auto-detect column mappings
        const autoMappings = autoDetectMappings(columnNames)
        setColumnMapping(autoMappings)

        // Show toast with auto-detection info
        const detectedFields = []
        if (autoMappings.name) detectedFields.push("Name")
        if (autoMappings.code) detectedFields.push("Code")
        if (autoMappings.brand) detectedFields.push("Brand")
        if (autoMappings.price) detectedFields.push("Price")
        if (autoMappings.barcode) detectedFields.push("Barcode")
        if (autoMappings.category) detectedFields.push("Category")
        if (autoMappings.quantity) detectedFields.push("Quantity")

        toast({
          title: "File uploaded",
          description: `Loaded ${totalRows} row(s) with ${columnNames.length} column(s). Products will be processed sequentially one-by-one.${detectedFields.length > 0 ? ` Auto-detected: ${detectedFields.join(", ")}` : ""}`,
        })
      } catch (error) {
        console.error("Error parsing Excel:", error)
        toast({
          title: "Error parsing file",
          description: "Failed to parse the Excel file. Please check the format.",
          variant: "destructive",
        })
      }
    }

    reader.readAsBinaryString(uploadedFile)
  }, [toast])

  const handleMappingChange = (mapping: {
    name?: string
    code?: string
    brand?: string
    category?: string
    barcode?: string
    price?: string
    quantity?: string
  }) => {
    setColumnMapping(mapping)
  }

  const validateMapping = (): boolean => {
    if (!columnMapping.brand) {
      toast({
        title: "Mapping required",
        description: "Please map the 'Brand' column",
        variant: "destructive",
      })
      return false
    }

    if (!columnMapping.name && !columnMapping.code) {
      toast({
        title: "Mapping required",
        description: "Please map either 'Product Name' or 'Product Code' column",
        variant: "destructive",
      })
      return false
    }

    return true
  }

  // Polling function for job status
  const pollJobStatus = useCallback(async () => {
    if (!jobId) return null

    const response = await fetch(`/api/scrape/jobs/${jobId}`)
    if (!response.ok) {
      throw new Error("Failed to get job status")
    }
    return response.json()
  }, [jobId])

  // Use refs to track current values to prevent stale callbacks
  const jobIdRef = useRef<string | null>(null)
  const scrapeProgressRef = useRef(0)
  useEffect(() => {
    jobIdRef.current = jobId
  }, [jobId])
  useEffect(() => {
    scrapeProgressRef.current = scrapeProgress
  }, [scrapeProgress])

  // Memoize onSuccess callback to prevent infinite loops
  const handlePollSuccess = useCallback((data: {
    status: string
    results: ScrapeResult[]
    progress: number
    error?: string
    total_products: number
  }) => {
    // Guard: Don't process if jobId has changed (stale callback)
    if (!jobIdRef.current) return

    // Update results incrementally - merge new results with existing ones
    if (data.results && Array.isArray(data.results)) {
      setResults((prev) => {
        let hasChanges = false
        const newResults = [...prev]
        // Update results that have changed (not pending anymore)
        data.results.forEach((result, index) => {
          if (result && result.status !== "pending") {
            // Check if this result is different from the existing one
            const existingResult = newResults[index]
            if (!existingResult || 
                existingResult.status !== result.status ||
                existingResult.product !== result.product ||
                existingResult.error !== result.error) {
              // Preserve originalExcelRow from existing result
              newResults[index] = {
                ...result,
                originalExcelRow: existingResult?.originalExcelRow || result.originalExcelRow
              }
              hasChanges = true
            }
          } else if (result && result.status === "pending" && index < newResults.length) {
            // Keep existing result if it's already been processed
            // Only update if current result is still pending
            if (newResults[index].status === "pending") {
              // Preserve originalExcelRow from existing result
              newResults[index] = {
                ...result,
                originalExcelRow: newResults[index]?.originalExcelRow || result.originalExcelRow
              }
              hasChanges = true
            }
          } else if (index >= newResults.length) {
            // Add new pending result if we don't have one yet
            newResults.push(result)
            hasChanges = true
          }
        })
        // Only return new array if there were actual changes
        return hasChanges ? newResults : prev
      })
    }

    // Update progress only if it's different (avoid unnecessary updates)
    if (data.progress !== scrapeProgressRef.current) {
      setScrapeProgress(data.progress)
    }

    // Check if job is complete
    if (data.status === "completed" || data.status === "failed") {
      // Only update if we still have the same jobId
      if (jobIdRef.current) {
        setIsScraping(false)
        setJobId(null)
        jobIdRef.current = null
        if (data.status === "completed") {
          toast({
            title: "Scraping completed",
            description: `Successfully processed ${data.total_products} product(s)`,
            variant: "default",
          })
        } else {
          toast({
            title: "Scraping failed",
            description: data.error || "An error occurred during scraping",
            variant: "destructive",
          })
        }
      }
    }
  }, [toast])

  // Memoize onError callback
  const handlePollError = useCallback((err: Error) => {
    toast({
      title: "Polling error",
      description: err.message,
      variant: "destructive",
    })
    setIsScraping(false)
    setJobId(null)
  }, [toast])

  // Memoize shouldStop callback
  const shouldStopPolling = useCallback((data: {
    status: string
    results: ScrapeResult[]
    progress: number
    error?: string
    total_products: number
  }) => {
    return data.status === "completed" || data.status === "failed"
  }, [])

  // Polling hook
  const { data: jobStatus, error: pollingError } = usePolling<{
    status: string
    results: ScrapeResult[]
    progress: number
    error?: string
    total_products: number
  }>({
    pollFn: pollJobStatus,
    enabled: !!jobId && isScraping,
    interval: 5000, // Poll every 5 seconds
    onSuccess: handlePollSuccess,
    onError: handlePollError,
    shouldStop: shouldStopPolling,
  })

  const handleStartScraping = async () => {
    if (!validateMapping()) return
    if (excelData.length === 0) {
      toast({
        title: "No data",
        description: "Please upload an Excel file first",
        variant: "destructive",
      })
      return
    }

    // Note: batchSize is kept for backward compatibility but not used for parallelization
    // Products are processed sequentially one-by-one

    setIsScraping(true)
    setScrapeProgress(0)
    setResults([])
    setJobId(null)

    // Map Excel data to product requests, keeping track of original row indices
    const productsWithIndices: Array<{ product: MappedProduct; excelRowIndex: number }> = excelData.map((row, excelRowIndex) => {
      const product: MappedProduct = {
        brand: String(row[columnMapping.brand!] || "").trim(),
      }

      if (columnMapping.name && row[columnMapping.name]) {
        product.name = String(row[columnMapping.name]).trim()
      }
      if (columnMapping.code && row[columnMapping.code]) {
        product.code = String(row[columnMapping.code]).trim()
      }
      if (columnMapping.price && row[columnMapping.price]) {
        product.price = String(row[columnMapping.price]).trim()
      }
      if (columnMapping.barcode && row[columnMapping.barcode]) {
        product.barcode = String(row[columnMapping.barcode]).trim()
      }
      if (columnMapping.category && row[columnMapping.category]) {
        product.category = String(row[columnMapping.category]).trim()
      }
      if (columnMapping.quantity && row[columnMapping.quantity]) {
        product.quantity = String(row[columnMapping.quantity]).trim()
      }

      return { product, excelRowIndex }
    })

    // Filter out invalid products, but keep the index mapping
    const filteredValidProductsWithIndices = productsWithIndices.filter(
      ({ product }) => product.brand && (product.name || product.code)
    )

    if (filteredValidProductsWithIndices.length === 0) {
      toast({
        title: "No valid products",
        description: "No products found with valid name/code and brand",
        variant: "destructive",
      })
      setIsScraping(false)
      return
    }

    // Extract just the products for the API call
    const filteredValidProducts = filteredValidProductsWithIndices.map(({ product }) => product)

    // Store valid products for later use
    setValidProducts(filteredValidProducts)

    // Process all products sequentially one-by-one
    const totalProducts = filteredValidProducts.length
    
    toast({
      title: "Starting bulk scrape",
      description: `Processing ${totalProducts} product(s) sequentially one-by-one.`,
      variant: "default",
    })

    // Initialize results with pending status for all products
    // Map each product to its original Excel row using the stored index
    const initialResults: ScrapeResult[] = filteredValidProductsWithIndices.map(({ product, excelRowIndex }) => {
      const originalExcelRow = excelData[excelRowIndex]
      
      return {
        status: "pending" as const,
        originalData: product,
        originalExcelRow,
      }
    })
    setResults(initialResults)

    try {
      const response = await fetch("/api/scrape/bulk", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          products: filteredValidProducts,
          batchSize: 1, // Not used for parallelization, kept for backward compatibility
          batchDelay,
          navigationDelay,
        }),
      })

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}))
        throw new Error(errorData.error || "Failed to start bulk scraping")
      }

      const data = await response.json()
      if (data.job_id) {
        setJobId(data.job_id)
      } else {
        throw new Error("No job ID returned")
      }
    } catch (error) {
      console.error("Scraping error:", error)
      toast({
        title: "Scraping failed",
        description: error instanceof Error ? error.message : "An error occurred during scraping",
        variant: "destructive",
      })
      // Update results to show errors
      setResults((prev) =>
        prev.map((r) =>
          r.status === "pending"
            ? {
                ...r,
                status: "error" as const,
                error: error instanceof Error ? error.message : "Unknown error",
              }
            : r
        )
      )
      setIsScraping(false)
      setJobId(null)
    }
  }

  type JobPayload = {
    status: string
    results: ScrapeResult[]
    progress: number
    error?: string
    total_products: number
  }

  const pollJobUntilComplete = useCallback(
    async (id: string, intervalMs = 2000, maxAttempts = 300): Promise<JobPayload> => {
      for (let attempt = 0; attempt < maxAttempts; attempt++) {
        const res = await fetch(`/api/scrape/jobs/${id}`)
        if (!res.ok) throw new Error("Failed to get job status")
        const data: JobPayload = await res.json()
        if (data.status === "completed" || data.status === "failed") return data
        await new Promise((r) => setTimeout(r, intervalMs))
      }
      throw new Error("Polling timeout: job did not complete")
    },
    []
  )

  const handleRetryOne = useCallback(
    async (index: number) => {
      const result = results[index]
      if (!result || result.status !== "error") return
      if (isScraping || isRetryingAll) return

      const originalExcelRow = result.originalExcelRow
      setRetryingIndices((prev) => new Set(prev).add(index))
      setResults((prev) => {
        const next = [...prev]
        next[index] = { ...prev[index], status: "pending" as const }
        return next
      })

      try {
        const bulkRes = await fetch("/api/scrape/bulk", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            products: [result.originalData],
            batchSize: 1,
            batchDelay: 0,
            navigationDelay,
          }),
        })
        if (!bulkRes.ok) {
          const err = await bulkRes.json().catch(() => ({}))
          throw new Error(err.error || "Failed to start retry")
        }
        const { job_id } = await bulkRes.json()
        if (!job_id) throw new Error("No job ID returned")

        const payload = await pollJobUntilComplete(job_id)
        const jobResult = payload.results?.[0]

        setResults((prev) => {
          const next = [...prev]
          next[index] = jobResult
            ? { ...jobResult, originalExcelRow: originalExcelRow ?? prev[index]?.originalExcelRow }
            : { ...prev[index], status: "error" as const, error: payload.error || "Unknown error" }
          return next
        })

        if (jobResult?.status === "success") {
          toast({ title: "Retry successful", description: "Product scraped successfully." })
        } else {
          toast({
            title: "Retry failed",
            description: jobResult?.error || payload.error || "Scraping failed",
            variant: "destructive",
          })
        }
      } catch (e) {
        const msg = e instanceof Error ? e.message : "Retry failed"
        toast({ title: "Retry failed", description: msg, variant: "destructive" })
        setResults((prev) => {
          const next = [...prev]
          next[index] = { ...prev[index], status: "error" as const, error: msg }
          return next
        })
      } finally {
        setRetryingIndices((prev) => {
          const next = new Set(prev)
          next.delete(index)
          return next
        })
      }
    },
    [results, isScraping, isRetryingAll, pollJobUntilComplete, toast]
  )

  const handleRetryAll = useCallback(async () => {
    const errorIndices: number[] = []
    const errorProducts: MappedProduct[] = []
    results.forEach((r, i) => {
      if (r.status === "error") {
        errorIndices.push(i)
        errorProducts.push(r.originalData)
      }
    })
    if (errorIndices.length === 0) return
    if (isScraping || isRetryingAll) return

    setIsRetryingAll(true)
    setResults((prev) => {
      const next = [...prev]
      errorIndices.forEach((i) => {
        next[i] = { ...prev[i], status: "pending" as const }
      })
      return next
    })

    try {
      const bulkRes = await fetch("/api/scrape/bulk", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          products: errorProducts,
          batchSize: 1, // Not used for parallelization, kept for backward compatibility
          batchDelay,
          navigationDelay,
        }),
      })
      if (!bulkRes.ok) {
        const err = await bulkRes.json().catch(() => ({}))
        throw new Error(err.error || "Failed to start retry")
      }
      const { job_id } = await bulkRes.json()
      if (!job_id) throw new Error("No job ID returned")

      const payload = await pollJobUntilComplete(job_id)
      const jobResults = payload.results ?? []

      setResults((prev) => {
        const next = [...prev]
        errorIndices.forEach((idx, i) => {
          const jobResult = jobResults[i]
          const existing = prev[idx]
          const originalExcelRow = existing?.originalExcelRow
          next[idx] = jobResult
            ? { ...jobResult, originalExcelRow: originalExcelRow ?? next[idx]?.originalExcelRow }
            : { ...existing, status: "error" as const, error: payload.error || "Unknown error" }
        })
        return next
      })

      const ok = jobResults.filter((r) => r?.status === "success").length
      const fail = errorIndices.length - ok
      if (fail === 0) {
        toast({ title: "Retry all complete", description: `All ${ok} product(s) scraped successfully.` })
      } else {
        toast({
          title: "Retry all complete",
          description: `${ok} succeeded, ${fail} failed.`,
          variant: fail > 0 ? "destructive" : "default",
        })
      }
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Retry all failed"
      toast({ title: "Retry all failed", description: msg, variant: "destructive" })
      setResults((prev) => {
        const next = [...prev]
        errorIndices.forEach((i) => {
          next[i] = { ...prev[i], status: "error" as const, error: msg }
        })
        return next
      })
    } finally {
      setIsRetryingAll(false)
    }
  }, [results, isScraping, isRetryingAll, batchSize, batchDelay, navigationDelay, pollJobUntilComplete, toast])

  return (
    <div className="space-y-8">
      {/* File Upload */}
      <Card>
        <CardHeader>
          <CardTitle>Upload Excel File</CardTitle>
          <CardDescription>
            Upload an Excel file (.xlsx or .xls) containing product information
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div className="flex items-center gap-4">
              <Label htmlFor="excel-upload" className="cursor-pointer">
                <div className="flex items-center gap-2 px-4 py-2 border rounded-md hover:bg-accent transition-colors">
                  <UploadIcon className="w-4 h-4" />
                  Choose Excel File
                </div>
              </Label>
              <Input
                id="excel-upload"
                type="file"
                accept=".xlsx,.xls"
                onChange={handleFileUpload}
                className="hidden"
              />
              {file && (
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <FileSpreadsheetIcon className="w-4 h-4" />
                  {file.name}
                </div>
              )}
            </div>

            {excelData.length > 0 && (
              <div className="mt-4 p-4 bg-muted rounded-md">
                <p className="text-sm">
                  <strong>{excelData.length}</strong> row(s) loaded with{" "}
                  <strong>{columns.length}</strong> column(s)
                </p>
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Column Mapping */}
      {columns.length > 0 && (
        <ColumnMapper
          columns={columns}
          mapping={columnMapping}
          onMappingChange={handleMappingChange}
        />
      )}

      {/* Processing Configuration */}
      {columns.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Processing Configuration</CardTitle>
            <CardDescription>
              Configure how products are scraped sequentially (one-by-one)
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="product-delay">Delay Between Products (ms)</Label>
                <Input
                  id="product-delay"
                  type="number"
                  min="0"
                  max="10000"
                  step="100"
                  value={batchDelay}
                  onChange={(e) => setBatchDelay(parseInt(e.target.value) || 1000)}
                />
                <p className="text-xs text-muted-foreground">
                  Delay between each product to avoid rate limiting (0-10000ms)
                </p>
              </div>
              <div className="space-y-2">
                <Label htmlFor="navigation-delay">Navigation Delay (ms)</Label>
                <Input
                  id="navigation-delay"
                  type="number"
                  min="0"
                  max="10000"
                  step="100"
                  value={navigationDelay}
                  onChange={(e) => setNavigationDelay(parseInt(e.target.value) || 0)}
                />
                <p className="text-xs text-muted-foreground">
                  Delay between each page navigation to prevent overloading sites (0-10000ms)
                </p>
              </div>
            </div>
            {excelData.length > 0 && (
              <div className="mt-4 p-4 bg-muted rounded-md">
                <p className="text-sm">
                  Estimated time: ~
                  {Math.ceil(
                    excelData.length * ((batchDelay / 1000) + 3)
                  )}{" "}
                  seconds (approximate, ~3 seconds per product + delays)
                </p>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Start Scraping Button */}
      {columns.length > 0 && (
        <Card>
          <CardContent className="pt-6">
            <Button
              onClick={handleStartScraping}
              disabled={isScraping}
              className="w-full"
              size="lg"
            >
              {isScraping ? (
                <>
                  <span className="animate-spin mr-2">⏳</span>
                  Scraping in progress...
                </>
              ) : (
                <>
                  <PlayIcon className="w-4 h-4 mr-2" />
                  Start Scraping
                </>
              )}
            </Button>
            {isScraping && (
              <div className="mt-4 space-y-2">
                <Progress value={scrapeProgress} />
                <p className="text-sm text-center text-muted-foreground">
                  {scrapeProgress}% complete
                </p>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Results */}
      {results.length > 0 && (
        <BulkResultsTable
          results={results}
          isScraping={isScraping}
          onRetryOne={handleRetryOne}
          onRetryAll={handleRetryAll}
          isRetryingAll={isRetryingAll}
          retryingIndices={retryingIndices}
        />
      )}
    </div>
  )
}
