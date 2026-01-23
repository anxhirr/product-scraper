import { type NextRequest, NextResponse } from "next/server"
import { normalizeBrandName } from "@/lib/brand-normalizer"

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000"

interface ScrapeRequest {
  name?: string
  code?: string
  brand: string
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
  code: string
): Promise<ProductData> {
  // Parse specifications first
  const parsedSpecs = parseSpecifications(backendProduct.specifications)

  return {
    name: backendProduct.title,
    code: backendProduct.sku,
    price: backendProduct.price,
    description: backendProduct.description || undefined,
    specifications: Object.keys(parsedSpecs).length > 0 ? parsedSpecs : undefined,
    images: backendProduct.images || [],
    primaryImage: backendProduct.primary_image || "",
    sourceUrl: backendProduct.url,
  }
}

export async function POST(request: NextRequest) {
  try {
    const body: ScrapeRequest = await request.json()
    const { name, code, brand } = body

    if (!brand) {
      return NextResponse.json(
        { error: "Missing required field: brand is required" },
        { status: 400 }
      )
    }

    // At least one of name or code must be provided
    if (!name && !code) {
      return NextResponse.json(
        { error: "Missing required field: either name or code must be provided" },
        { status: 400 }
      )
    }

    // Create async job on backend
    const backendUrl = `${BACKEND_URL}/jobs`
    const response = await fetch(backendUrl, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        products: [
          {
            name: name,
            code: code,
            brand: normalizeBrandName(brand),
          },
        ],
      }),
    })

    if (!response.ok) {
      const errorText = await response.text()
      console.error(`Backend error (${response.status}):`, errorText)
      return NextResponse.json(
        { error: `Backend API error: ${errorText || response.statusText}` },
        { status: response.status }
      )
    }

    const jobData: { job_id: string } = await response.json()

    return NextResponse.json({ job_id: jobData.job_id })
  } catch (error) {
    console.error("Scraping error:", error)
    return NextResponse.json(
      { error: error instanceof Error ? error.message : "Failed to start scraping job" },
      { status: 500 }
    )
  }
}
