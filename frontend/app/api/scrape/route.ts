import { type NextRequest, NextResponse } from "next/server"
import { translateToAlbanian } from "@/lib/translator"

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
  url: string
}

interface ProductData {
  name: string
  nameOriginal?: string
  code: string
  price?: string
  brand?: string
  description?: string
  descriptionOriginal?: string
  specifications?: Record<string, string>
  specificationsOriginal?: Record<string, string>
  images?: string[]
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
        const colonIndex = line.indexOf(":")
        if (colonIndex > 0) {
          const key = line.substring(0, colonIndex).trim()
          const value = line.substring(colonIndex + 1).trim()
          if (key && value) {
            result[key] = value
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
      
      // Fallback: try simple colon split for single key-value pair
      const colonIndex = specs.indexOf(":")
      if (colonIndex > 0) {
        const key = specs.substring(0, colonIndex).trim()
        const value = specs.substring(colonIndex + 1).trim()
        if (key && value) {
          result[key] = value
          return result
        }
      }
    }
  }
  // If all else fails, return as a single key-value pair
  return { Specifications: specs }
}

// Map backend Product to frontend ProductData
async function mapProductToProductData(
  backendProduct: BackendProduct,
  code: string
): Promise<ProductData> {
  // Parse specifications first
  const parsedSpecs = parseSpecifications(backendProduct.specifications)

  // Translate name, description and specification values in parallel
  const translateName = backendProduct.title
    ? translateToAlbanian(backendProduct.title)
    : Promise.resolve(undefined)

  const translateDescription = backendProduct.description
    ? translateToAlbanian(backendProduct.description)
    : Promise.resolve(undefined)

  // Translate specification values in parallel (keep keys as-is)
  const translatedSpecs: Record<string, string> = {}
  let translateSpecs: Promise<void> = Promise.resolve()
  
  if (parsedSpecs && Object.keys(parsedSpecs).length > 0) {
    const specEntries = Object.entries(parsedSpecs)
    const translationPromises = specEntries.map(async ([key, value]) => {
      const translatedValue = value ? await translateToAlbanian(value) : value
      return [key, translatedValue] as [string, string]
    })
    translateSpecs = Promise.all(translationPromises).then((translatedEntries) => {
      translatedEntries.forEach(([key, value]) => {
        translatedSpecs[key] = value
      })
    })
  }

  // Wait for name, description and specifications translations to complete
  const [translatedName, translatedDescription] = await Promise.all([translateName, translateDescription, translateSpecs])

  return {
    name: translatedName || backendProduct.title,
    nameOriginal: backendProduct.title || undefined,
    code: backendProduct.sku || code, // Fallback to provided code if sku is empty
    price: backendProduct.price,
    description: translatedDescription,
    descriptionOriginal: backendProduct.description || undefined,
    specifications: Object.keys(translatedSpecs).length > 0 ? translatedSpecs : undefined,
    specificationsOriginal: Object.keys(parsedSpecs).length > 0 ? parsedSpecs : undefined,
    images: backendProduct.images || [],
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
            brand: brand,
          },
        ],
        batch_size: 1,
        batch_delay: 0,
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
