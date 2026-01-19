import ProductScraperForm from "@/components/product-scraper-form"
import { SearchIcon, FileSpreadsheetIcon } from "lucide-react"
import Link from "next/link"
import { Button } from "@/components/ui/button"

export default function Home() {
  return (
    <main className="min-h-screen bg-background">
      <div className="container mx-auto px-4 py-12 max-w-6xl">
        <div className="flex flex-col items-center text-center mb-12 space-y-4">
          <div className="flex items-center justify-center w-16 h-16 rounded-full bg-primary/10 mb-2">
            <SearchIcon className="w-8 h-8 text-primary" />
          </div>
          <h1 className="text-4xl md:text-5xl font-bold tracking-tight text-balance">Product Information Scraper</h1>
          <p className="text-lg md:text-xl text-muted-foreground max-w-2xl text-balance">
            {
              "Enter product details to automatically find descriptions, specifications, and photos from official brand websites"
            }
          </p>
          <div className="pt-4">
            <Button variant="outline" asChild>
              <Link href="/bulk">
                <FileSpreadsheetIcon className="w-4 h-4 mr-2" />
                Bulk Upload (Excel)
              </Link>
            </Button>
          </div>
        </div>

        <ProductScraperForm />
      </div>
    </main>
  )
}
