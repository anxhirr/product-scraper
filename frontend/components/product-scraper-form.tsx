"use client"

import type React from "react"

import { useState, useEffect } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Button } from "@/components/ui/button"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { SearchIcon } from "lucide-react"
import ProductResults from "@/components/product-results"

export interface ProductData {
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

const STORAGE_KEY = "product-scraper-selected-site"

export default function ProductScraperForm() {
  const [formData, setFormData] = useState({
    name: "",
    code: "",
    site: "",
  })
  const [sites, setSites] = useState<string[]>([])
  const [loadingSites, setLoadingSites] = useState(true)
  const [loading, setLoading] = useState(false)
  const [results, setResults] = useState<ProductData | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [isMounted, setIsMounted] = useState(false)

  // Mark component as mounted (client-side only)
  useEffect(() => {
    setIsMounted(true)
  }, [])

  // Save site to localStorage whenever it changes (but not on initial mount)
  useEffect(() => {
    if (isMounted && formData.site && sites.length > 0) {
      // Only save if the site is actually in the available sites list
      if (sites.includes(formData.site)) {
        localStorage.setItem(STORAGE_KEY, formData.site)
      }
    }
  }, [formData.site, sites, isMounted])

  // Fetch available sites on component mount
  useEffect(() => {
    const fetchSites = async () => {
      try {
        const response = await fetch("/api/scrape/sites")
        if (!response.ok) {
          throw new Error("Failed to fetch available sites")
        }
        const sitesData = await response.json()
        setSites(sitesData)
        
        // Restore saved site if it's still valid, otherwise use first site
        if (sitesData.length > 0) {
          const savedSite = isMounted ? localStorage.getItem(STORAGE_KEY) : null
          const siteToUse = savedSite && sitesData.includes(savedSite) 
            ? savedSite 
            : sitesData[0]
          
          // Always set the site after fetching (this ensures it's set even if initial state was empty)
          setFormData((prev) => ({ ...prev, site: siteToUse }))
        }
      } catch (err) {
        console.error("Error fetching sites:", err)
        setError("Failed to load available sites")
      } finally {
        setLoadingSites(false)
      }
    }

    fetchSites()
  }, [isMounted])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    // Validate that at least one of name or code is provided
    if (!formData.name && !formData.code) {
      setError("Please provide either a product name or product code")
      return
    }

    setLoading(true)
    setError(null)
    setResults(null)

    try {
      const response = await fetch("/api/scrape", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(formData),
      })

      if (!response.ok) {
        throw new Error("Failed to scrape product data")
      }

      const data = await response.json()
      setResults(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : "An error occurred")
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-8">
      <Card>
        <CardHeader>
          <CardTitle>Product Details</CardTitle>
          <CardDescription>Enter either the product name or product code to search for details on the brand website</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="space-y-2">
                <Label htmlFor="site">Website</Label>
                <Select
                  value={formData.site}
                  onValueChange={(value) => setFormData({ ...formData, site: value })}
                  disabled={loadingSites}
                  required
                >
                  <SelectTrigger id="site" className="w-full">
                    <SelectValue placeholder={loadingSites ? "Loading sites..." : "Select a website"} />
                  </SelectTrigger>
                  <SelectContent>
                    {sites.map((site) => (
                      <SelectItem key={site} value={site}>
                        {site}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label htmlFor="code">Product Code</Label>
                <Input
                  id="code"
                  placeholder="e.g., SKU-12345"
                  value={formData.code}
                  onChange={(e) => setFormData({ ...formData, code: e.target.value })}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="name">Product Name</Label>
                <Input
                  id="name"
                  placeholder="e.g., iPhone 15 Pro"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                />
              </div>
            </div>
            <Button type="submit" disabled={loading} className="w-full md:w-auto">
              {loading ? (
                <>
                  <span className="animate-spin mr-2">⏳</span>
                  Searching...
                </>
              ) : (
                <>
                  <SearchIcon className="w-4 h-4 mr-2" />
                  Search Product
                </>
              )}
            </Button>
          </form>
        </CardContent>
      </Card>

      {error && (
        <Card className="border-destructive">
          <CardContent className="pt-6">
            <p className="text-destructive">{error}</p>
          </CardContent>
        </Card>
      )}

      {results && <ProductResults data={results} />}
    </div>
  )
}
