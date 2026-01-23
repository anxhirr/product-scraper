import { type NextRequest, NextResponse } from "next/server"

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000"

interface BackendProduct {
  title: string
  sku: string
  price: string
  description: string
  specifications: string
  images: string[]
  primary_image: string
  url: string
}

interface BackendBatchResponse {
  product?: BackendProduct
  error?: string
  status: "success" | "error"
  category?: string
  barcode?: string
  price?: string
  quantity?: string
}

interface ProductData {
  name: string
  code: string
  price?: string
  brand?: string
  description?: string
  specifications?: Record<string, string>
  images?: string[]
  primaryImage?: string
  sourceUrl?: string
}

interface BatchProductRequest {
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
  originalData: BatchProductRequest
}

interface BackendJobStatusResponse {
  status: string
  results: (BackendBatchResponse | null)[]
  progress: number
  error?: string
  total_products: number
  original_products?: Array<{
    name?: string
    code?: string
    brand?: string
    category?: string
    barcode?: string
    price?: string
    quantity?: string
  }>
}

// Helper function to parse specifications string into Record<string, string>
function parseSpecifications(specs: string): Record<string, string> {
  try {
    // Try parsing as JSON first
    const parsed = JSON.parse(specs)
    if (typeof parsed === "object" && parsed !== null) {
      return parsed
    }
  } catch {
    // If not JSON, try parsing as key-value pairs
    const result: Record<string, string> = {}
    
    // First, try splitting by newlines (preferred format)
    const lines = specs.split("\n").filter((line) => line.trim())
    if (lines.length > 1) {
      // Multiple lines - parse each line
      for (const line of lines) {
        // Try colon-separated format first: "Key: Value"
        const colonIndex = line.indexOf(":")
        if (colonIndex > 0) {
          const key = line.substring(0, colonIndex).trim()
          const value = line.substring(colonIndex + 1).trim()
          if (key && value) {
            result[key] = value
          }
        } else {
          // Try format without colon: "Key (Unit) Value" or "Key Value"
          // Pattern: "Key (Unit) Value" or "Key Value"
          const parenMatch = line.match(/^(.+?)\s*\([^)]+\)\s+(.+)$/)
          if (parenMatch) {
            // Format: "Key (Unit) Value"
            const key = parenMatch[1].trim()
            const value = parenMatch[2].trim()
            if (key && value) {
              result[key] = value
            }
          } else {
            // Try simple space-separated: "Key Value" (take last space as separator)
            const lastSpaceIndex = line.lastIndexOf(" ")
            if (lastSpaceIndex > 0) {
              const key = line.substring(0, lastSpaceIndex).trim()
              const value = line.substring(lastSpaceIndex + 1).trim()
              if (key && value) {
                result[key] = value
              }
            }
          }
        }
      }
      if (Object.keys(result).length > 0) {
        return result
      }
    } else {
      // Single line - try to parse multiple key-value pairs on the same line
      // Pattern: "Key: Value Key2: Value2 Key3: Value3"
      // Split by finding patterns like " Key: " (space, text, colon, space) or start of string
      const keyValuePattern = /(?:^|\s)([^:]+?):\s*([^:]+?)(?=\s+[^:]+:|$)/g
      let match
      while ((match = keyValuePattern.exec(specs)) !== null) {
        const key = match[1].trim()
        const value = match[2].trim()
        if (key && value) {
          result[key] = value
        }
      }
      if (Object.keys(result).length > 0) {
        return result
      }
    }
  }
  return {}
}

// Map backend Product to frontend ProductData
async function mapProductToProductData(
  backendProduct: BackendProduct,
  code: string,
  brand?: string,
  excelPrice?: string,
  excelBarcode?: string,
  excelCategory?: string,
  excelQuantity?: string
): Promise<ProductData> {
  // Parse specifications first
  const parsedSpecs = parseSpecifications(backendProduct.specifications)

  // Use Excel price if provided, otherwise use scraped price
  const finalPrice = excelPrice || backendProduct.price

  return {
    name: backendProduct.title,
    code: backendProduct.sku,
    price: finalPrice,
    brand: brand || undefined,
    description: backendProduct.description || undefined,
    specifications:
      Object.keys(parsedSpecs).length > 0 ? parsedSpecs : undefined,
    images: backendProduct.images || [],
    primaryImage: backendProduct.primary_image || "",
    sourceUrl: backendProduct.url,
  }
}

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ jobId: string }> | { jobId: string } }
) {
  try {
    // Handle params as either Promise (Next.js 15+) or object (Next.js 14)
    const resolvedParams = params instanceof Promise ? await params : params
    const jobId = resolvedParams?.jobId

    if (!jobId || typeof jobId !== "string") {
      console.error("Job ID missing or invalid:", { jobId, params: resolvedParams })
      return NextResponse.json(
        { error: "Job ID is required" },
        { status: 400 }
      )
    }

    // Get job status from backend
    const backendUrl = `${BACKEND_URL}/jobs/${jobId}/status`
    const response = await fetch(backendUrl, {
      method: "GET",
      headers: {
        "Content-Type": "application/json",
      },
    })

    if (!response.ok) {
      if (response.status === 404) {
        return NextResponse.json(
          { error: "Job not found" },
          { status: 404 }
        )
      }
      const errorText = await response.text()
      console.error(`Backend error (${response.status}):`, errorText)
      return NextResponse.json(
        { error: `Backend API error: ${errorText || response.statusText}` },
        { status: response.status }
      )
    }

    const backendStatus: BackendJobStatusResponse = await response.json()

    // Map results using original products data from backend
    const originalProducts = backendStatus.original_products || []
    const results: ScrapeResult[] = await Promise.all(
      backendStatus.results.map(async (backendResult, index) => {
      const originalProduct = originalProducts[index] || {}
      const originalData: BatchProductRequest = {
        brand: originalProduct.brand || "",
        name: originalProduct.name,
        code: originalProduct.code,
        category: originalProduct.category,
        barcode: originalProduct.barcode,
        price: originalProduct.price,
        quantity: originalProduct.quantity,
      }

      if (!backendResult) {
        return {
          status: "pending" as const,
          originalData,
        }
      }

      if (backendResult.status === "success" && backendResult.product) {
        const excelPrice = backendResult.price || originalData.price
        const excelBarcode = backendResult.barcode || originalData.barcode
        const excelCategory = backendResult.category || originalData.category
        const excelQuantity = backendResult.quantity || originalData.quantity

        const productData = await mapProductToProductData(
          backendResult.product,
          backendResult.product.sku,
          originalData.brand,
          excelPrice,
          excelBarcode,
          excelCategory,
          excelQuantity
        )

        return {
          status: "success" as const,
          product: productData,
          originalData: {
            ...originalData,
            category: backendResult.category || originalData.category,
            barcode: backendResult.barcode || originalData.barcode,
            price: backendResult.price || originalData.price,
            quantity: backendResult.quantity || originalData.quantity,
          },
        }
      } else {
        return {
          error: backendResult.error || "Unknown error",
          status: "error" as const,
          originalData: {
            ...originalData,
            category: backendResult.category || originalData.category,
            barcode: backendResult.barcode || originalData.barcode,
            price: backendResult.price || originalData.price,
            quantity: backendResult.quantity || originalData.quantity,
          },
        }
      }
    }))

    return NextResponse.json({
      status: backendStatus.status,
      results: results,
      progress: backendStatus.progress,
      error: backendStatus.error,
      total_products: backendStatus.total_products,
    })
  } catch (error) {
    console.error("Job status error:", error)
    return NextResponse.json(
      {
        error: error instanceof Error ? error.message : "Failed to get job status",
      },
      { status: 500 }
    )
  }
}
