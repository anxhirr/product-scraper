import { type NextRequest, NextResponse } from "next/server"
import { normalizeBrandName } from "@/lib/brand-normalizer"

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000"

interface BatchProductRequest {
  name?: string
  code?: string
  brand: string
  category?: string
  barcode?: string
  price?: string
  quantity?: string
}

interface BatchRequest {
  products: BatchProductRequest[]
  maxWorkers?: number
}

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

interface ScrapeResult {
  product?: ProductData
  error?: string
  status: "success" | "error" | "pending"
  originalData: BatchProductRequest
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

export async function POST(request: NextRequest) {
  try {
    const body: BatchRequest = await request.json()
    const { products, maxWorkers } = body

    if (!products || products.length === 0) {
      return NextResponse.json(
        { error: "No products provided" },
        { status: 400 }
      )
    }

    // Create async job on backend - all products are processed (no limit)
    const backendUrl = `${BACKEND_URL}/jobs`
    const response = await fetch(backendUrl, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        products: products.map((p) => ({
          name: p.name,
          code: p.code,
          brand: normalizeBrandName(p.brand),
          category: p.category,
          barcode: p.barcode,
          price: p.price,
          quantity: p.quantity,
        })),
        max_workers: maxWorkers,
      }),
    })

    if (!response.ok) {
      let errorMessage = "Backend API error"
      try {
        const errorData = await response.json()
        errorMessage = errorData.detail || errorData.error || errorMessage
      } catch {
        const errorText = await response.text()
        errorMessage = errorText || response.statusText || errorMessage
      }
      console.error(`Backend error (${response.status}):`, errorMessage)
      return NextResponse.json(
        { error: errorMessage },
        { status: response.status }
      )
    }

    const jobData: { job_id: string } = await response.json()

    return NextResponse.json({ job_id: jobData.job_id })
  } catch (error) {
    console.error("Bulk scraping error:", error)
    return NextResponse.json(
      {
        error: error instanceof Error ? error.message : "Failed to start scraping job",
      },
      { status: 500 }
    )
  }
}
