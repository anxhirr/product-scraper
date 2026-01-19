import { type NextRequest, NextResponse } from "next/server"
import { translateToAlbanian } from "@/lib/translator"

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
  batchSize: number
  batchDelay: number
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
  code: string,
  brand?: string,
  excelPrice?: string,
  excelBarcode?: string,
  excelCategory?: string,
  excelQuantity?: string
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
  const [translatedName, translatedDescription] = await Promise.all([
    translateName,
    translateDescription,
    translateSpecs,
  ])

  // Merge Excel values into specifications if provided
  const finalSpecs: Record<string, string> = { ...translatedSpecs }
  if (excelBarcode) {
    finalSpecs["Barcode"] = excelBarcode
  }
  if (excelCategory) {
    finalSpecs["Category"] = excelCategory
  }
  if (excelQuantity) {
    finalSpecs["Quantity"] = excelQuantity
  }

  // Use Excel price if provided, otherwise use scraped price
  const finalPrice = excelPrice || backendProduct.price

  return {
    name: translatedName || backendProduct.title,
    nameOriginal: backendProduct.title || undefined,
    code: backendProduct.sku || code, // Fallback to provided code if sku is empty
    price: finalPrice,
    brand: brand || undefined,
    description: translatedDescription,
    descriptionOriginal: backendProduct.description || undefined,
    specifications:
      Object.keys(finalSpecs).length > 0 ? finalSpecs : undefined,
    specificationsOriginal:
      Object.keys(parsedSpecs).length > 0 ? parsedSpecs : undefined,
    images: backendProduct.images || [],
    sourceUrl: backendProduct.url,
  }
}

export async function POST(request: NextRequest) {
  try {
    const body: BatchRequest = await request.json()
    const { products, batchSize, batchDelay } = body

    if (!products || products.length === 0) {
      return NextResponse.json(
        { error: "No products provided" },
        { status: 400 }
      )
    }

    // Call backend batch API
    const backendUrl = `${BACKEND_URL}/search/batch`
    const response = await fetch(backendUrl, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        products: products.map((p) => ({
          name: p.name,
          code: p.code,
          brand: p.brand,
          category: p.category,
          barcode: p.barcode,
          price: p.price,
          quantity: p.quantity,
        })),
        batch_size: batchSize,
        batch_delay: batchDelay,
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

    const backendResults: BackendBatchResponse[] = await response.json()

    // Map backend results to frontend format and translate
    const results: ScrapeResult[] = await Promise.all(
      backendResults.map(async (backendResult, index) => {
        const originalData = products[index]

        if (backendResult.status === "success" && backendResult.product) {
          try {
            // Use preserved fields from backend response, fallback to original data
            const excelPrice = backendResult.price || originalData.price
            const excelBarcode = backendResult.barcode || originalData.barcode
            const excelCategory = backendResult.category || originalData.category
            const excelQuantity = backendResult.quantity || originalData.quantity

            const productData = await mapProductToProductData(
              backendResult.product,
              originalData.code || "",
              originalData.brand,
              excelPrice,
              excelBarcode,
              excelCategory,
              excelQuantity
            )
            return {
              product: productData,
              status: "success" as const,
              originalData,
            }
          } catch (error) {
            return {
              error:
                error instanceof Error
                  ? error.message
                  : "Failed to process product data",
              status: "error" as const,
              originalData,
            }
          }
        } else {
          return {
            error: backendResult.error || "Unknown error",
            status: "error" as const,
            originalData,
          }
        }
      })
    )

    return NextResponse.json({ results })
  } catch (error) {
    console.error("Bulk scraping error:", error)
    return NextResponse.json(
      {
        error: error instanceof Error ? error.message : "Failed to scrape products",
      },
      { status: 500 }
    )
  }
}
