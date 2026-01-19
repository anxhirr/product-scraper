"use client"

import type React from "react"
import { useState, useCallback } from "react"
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

interface ExcelRow {
  [key: string]: string | number | null
}

interface MappedProduct {
  name?: string
  code?: string
  site: string
  brand?: string
}

interface ScrapeResult {
  product?: ProductData
  error?: string
  status: "success" | "error" | "pending"
  originalData: MappedProduct
}

export default function BulkUploadForm() {
  const { toast } = useToast()
  const [excelData, setExcelData] = useState<ExcelRow[]>([])
  const [columns, setColumns] = useState<string[]>([])
  const [columnMapping, setColumnMapping] = useState<{
    name?: string
    code?: string
    site?: string
    brand?: string
  }>({})
  const [batchSize, setBatchSize] = useState(20)
  const [batchDelay, setBatchDelay] = useState(1000)
  const [isScraping, setIsScraping] = useState(false)
  const [scrapeProgress, setScrapeProgress] = useState(0)
  const [results, setResults] = useState<ScrapeResult[]>([])
  const [file, setFile] = useState<File | null>(null)

  // Auto-detect column mappings based on column names
  const autoDetectMappings = useCallback((columnNames: string[]) => {
    const mapping: {
      name?: string
      code?: string
      site?: string
      brand?: string
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

    // Patterns for site/website (English and Albanian)
    const sitePatterns = [
      /^site$/i,
      /^website$/i,
      /^web\s*site$/i,
      /^url$/i,
      /^source$/i,
      /^source\s*site$/i,
      /^scraper$/i,
      /^scraper\s*site$/i,
      // Albanian patterns
      /^faqja$/i,
      /^faqja\s*web$/i,
      /^website$/i,
      /^burimi$/i,
      /^faqja\s*e\s*burimit$/i,
      /^vendndodhja$/i,
      /^adresa$/i,
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

      // Check for site
      if (!mapping.site) {
        for (const pattern of sitePatterns) {
          if (pattern.test(normalized)) {
            mapping.site = col
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
        const jsonData: ExcelRow[] = XLSX.utils.sheet_to_json(worksheet, {
          raw: false,
          defval: null,
        })

        if (jsonData.length === 0) {
          toast({
            title: "Empty file",
            description: "The Excel file appears to be empty",
            variant: "destructive",
          })
          return
        }

        // Limit to 50 rows maximum
        const MAX_ROWS = 50
        const limitedData = jsonData.slice(0, MAX_ROWS)
        const totalRows = jsonData.length

        // Extract column names
        const columnNames = Object.keys(limitedData[0])
        setColumns(columnNames)
        setExcelData(limitedData)

        // Auto-detect column mappings
        const autoMappings = autoDetectMappings(columnNames)
        setColumnMapping(autoMappings)

        // Show toast with auto-detection info
        const detectedFields = []
        if (autoMappings.name) detectedFields.push("Name")
        if (autoMappings.code) detectedFields.push("Code")
        if (autoMappings.site) detectedFields.push("Site")
        if (autoMappings.brand) detectedFields.push("Brand")

        if (totalRows > MAX_ROWS) {
          toast({
            title: "File uploaded (limited)",
            description: `Loaded ${MAX_ROWS} of ${totalRows} row(s). Maximum ${MAX_ROWS} rows allowed.${detectedFields.length > 0 ? ` Auto-detected: ${detectedFields.join(", ")}` : ""}`,
            variant: "default",
          })
        } else {
          toast({
            title: "File uploaded",
            description: `Loaded ${totalRows} row(s) with ${columnNames.length} column(s).${detectedFields.length > 0 ? ` Auto-detected: ${detectedFields.join(", ")}` : ""}`,
          })
        }
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
    site?: string
    brand?: string
  }) => {
    setColumnMapping(mapping)
  }

  const validateMapping = (): boolean => {
    if (!columnMapping.site) {
      toast({
        title: "Mapping required",
        description: "Please map the 'Website/Site' column",
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

    // Validate batch size
    const validBatchSize = Math.max(1, Math.min(50, batchSize || 20))
    if (batchSize !== validBatchSize) {
      setBatchSize(validBatchSize)
      toast({
        title: "Batch size adjusted",
        description: `Batch size must be between 1 and 50. Set to ${validBatchSize}.`,
        variant: "default",
      })
    }

    setIsScraping(true)
    setScrapeProgress(0)
    setResults([])

    // Map Excel data to product requests
    const products: MappedProduct[] = excelData.map((row) => {
      const product: MappedProduct = {
        site: String(row[columnMapping.site!] || "").trim(),
      }

      if (columnMapping.name && row[columnMapping.name]) {
        product.name = String(row[columnMapping.name]).trim()
      }
      if (columnMapping.code && row[columnMapping.code]) {
        product.code = String(row[columnMapping.code]).trim()
      }
      if (columnMapping.brand && row[columnMapping.brand]) {
        product.brand = String(row[columnMapping.brand]).trim()
      }

      return product
    })

    // Filter out invalid products
    const validProducts = products.filter(
      (p) => p.site && (p.name || p.code)
    )

    if (validProducts.length === 0) {
      toast({
        title: "No valid products",
        description: "No products found with valid name/code and site",
        variant: "destructive",
      })
      setIsScraping(false)
      return
    }

    // Enforce maximum of 50 products
    const MAX_PRODUCTS = 50
    if (validProducts.length > MAX_PRODUCTS) {
      toast({
        title: "Too many products",
        description: `Maximum ${MAX_PRODUCTS} products allowed. Only the first ${MAX_PRODUCTS} will be processed.`,
        variant: "default",
      })
    }
    const productsToProcess = validProducts.slice(0, MAX_PRODUCTS)

    // Initialize results with pending status
    const initialResults: ScrapeResult[] = validProducts.map((p) => ({
      status: "pending",
      originalData: p,
    }))
    setResults(initialResults)

    try {
      const response = await fetch("/api/scrape/bulk", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          products: validProducts,
          batchSize: validBatchSize,
          batchDelay,
        }),
      })

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}))
        throw new Error(errorData.error || "Failed to start bulk scraping")
      }

      const data = await response.json()
      if (data.results && Array.isArray(data.results)) {
        setResults(data.results)
        setScrapeProgress(100)
      } else {
        throw new Error("Invalid response format")
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
    } finally {
      setIsScraping(false)
      setScrapeProgress(100)
    }
  }

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

      {/* Batch Configuration */}
      {columns.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Batch Configuration</CardTitle>
            <CardDescription>
              Configure how products are scraped in batches
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="batch-size">Batch Size</Label>
                <Input
                  id="batch-size"
                  type="number"
                  min="1"
                  max="50"
                  value={batchSize}
                  onChange={(e) => {
                    const value = parseInt(e.target.value)
                    if (!isNaN(value)) {
                      // Clamp value between 1 and 50
                      const clampedValue = Math.max(1, Math.min(50, value))
                      setBatchSize(clampedValue)
                    } else if (e.target.value === "") {
                      // Reset to default if empty
                      setBatchSize(20)
                    }
                  }}
                  onBlur={(e) => {
                    // Ensure valid value on blur
                    const value = parseInt(e.target.value)
                    if (isNaN(value) || value < 1 || value > 50) {
                      setBatchSize(20)
                    }
                  }}
                />
                <p className="text-xs text-muted-foreground">
                  Number of products to scrape in parallel (1-50)
                </p>
              </div>
              <div className="space-y-2">
                <Label htmlFor="batch-delay">Delay Between Batches (ms)</Label>
                <Input
                  id="batch-delay"
                  type="number"
                  min="0"
                  max="10000"
                  step="100"
                  value={batchDelay}
                  onChange={(e) => setBatchDelay(parseInt(e.target.value) || 1000)}
                />
                <p className="text-xs text-muted-foreground">
                  Delay to avoid rate limiting (0-10000ms)
                </p>
              </div>
            </div>
            {excelData.length > 0 && (
              <div className="mt-4 p-4 bg-muted rounded-md">
                <p className="text-sm">
                  Estimated time: ~
                  {Math.ceil(
                    (excelData.length / batchSize) * (batchDelay / 1000) +
                      excelData.length * 2
                  )}{" "}
                  seconds (approximate)
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
        <BulkResultsTable results={results} isScraping={isScraping} />
      )}
    </div>
  )
}
