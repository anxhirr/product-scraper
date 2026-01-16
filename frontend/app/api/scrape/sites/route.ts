import { NextResponse } from "next/server"

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000"

export async function GET() {
  try {
    const response = await fetch(`${BACKEND_URL}/sites`, {
      method: "GET",
      headers: {
        "Content-Type": "application/json",
      },
    })

    if (!response.ok) {
      throw new Error(`Backend responded with status ${response.status}`)
    }

    const sites = await response.json()
    return NextResponse.json(sites)
  } catch (error) {
    console.error("Error fetching sites:", error)
    return NextResponse.json(
      { error: "Failed to fetch available sites" },
      { status: 500 }
    )
  }
}
