import { type NextRequest, NextResponse } from "next/server"
import { translateToAlbanian } from "@/lib/translator"

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000"

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

  // Use translated specifications as-is (don't merge Excel barcode, category, quantity)
  const finalSpecs: Record<string, string> = { ...translatedSpecs }

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
    const results: ScrapeResult[] = backendStatus.results.map((backendResult, index) => {
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
        // Return partial product data, will be translated below
        return {
          status: "success" as const,
          product: {
            name: backendResult.product.title,
            code: backendResult.product.sku,
            price: backendResult.price || backendResult.product.price,
            description: backendResult.product.description,
            images: backendResult.product.images,
            sourceUrl: backendResult.product.url,
          } as ProductData, // Partial, will be translated below
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
    })

    // Translate results in parallel
    const translatedResults = await Promise.all(
      results.map(async (result, index) => {
        const backendResult = backendStatus.results[index]
        if (result.status === "success" && result.product && backendResult?.product) {
          const originalData = result.originalData
          
          try {
            const excelPrice = backendResult.price || originalData.price
            const excelBarcode = backendResult.barcode || originalData.barcode
            const excelCategory = backendResult.category || originalData.category
            const excelQuantity = backendResult.quantity || originalData.quantity

            const productData = await mapProductToProductData(
              backendResult.product,
              result.product.code || "",
              originalData.brand,
              excelPrice,
              excelBarcode,
              excelCategory,
              excelQuantity
            )
            
            return {
              ...result,
              product: productData,
            }
          } catch (error) {
            return {
              ...result,
              status: "error" as const,
              error: error instanceof Error ? error.message : "Failed to process product data",
            }
          }
        }
        return result
      })
    )

    return NextResponse.json({
      status: backendStatus.status,
      results: translatedResults,
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
