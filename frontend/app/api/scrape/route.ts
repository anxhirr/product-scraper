import { type NextRequest, NextResponse } from "next/server"
import { translateToAlbanian } from "@/lib/translator"

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000"

interface ScrapeRequest {
  name: string
  code: string
  site: string
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
    // If not JSON, try parsing as key-value pairs (e.g., "key: value\nkey2: value2")
    const lines = specs.split("\n").filter((line) => line.trim())
    const result: Record<string, string> = {}
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

  // Translate description and specification values in parallel
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

  // Wait for both description and specifications translations to complete
  const [translatedDescription] = await Promise.all([translateDescription, translateSpecs])

  return {
    name: backendProduct.title,
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
    const { name, code, site } = body

    if (!name || !code || !site) {
      return NextResponse.json(
        { error: "Missing required fields: name, code, and site are required" },
        { status: 400 }
      )
    }

    // Call backend API: /search/{site}/{query}
    // Using product name as query (per plan specification)
    const query = encodeURIComponent(name)
    const backendUrl = `${BACKEND_URL}/search/${encodeURIComponent(site)}/${query}`

    const response = await fetch(backendUrl, {
      method: "GET",
      headers: {
        "Content-Type": "application/json",
      },
    })

    if (!response.ok) {
      const errorText = await response.text()
      console.error(`Backend error (${response.status}):`, errorText)
      return NextResponse.json(
        { error: `Backend API error: ${errorText || response.statusText}` },
        { status: response.status }
      )
    }

    const backendProduct: BackendProduct = await response.json()

    // Map backend Product to frontend ProductData and translate to Albanian
    const productData = await mapProductToProductData(backendProduct, code)

    return NextResponse.json(productData)
  } catch (error) {
    console.error("Scraping error:", error)
    return NextResponse.json(
      { error: error instanceof Error ? error.message : "Failed to scrape product data" },
      { status: 500 }
    )
  }
}
