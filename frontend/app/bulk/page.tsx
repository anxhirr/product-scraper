import BulkUploadForm from "@/components/bulk-upload-form"
import { FileSpreadsheetIcon } from "lucide-react"
import Link from "next/link"
import { Button } from "@/components/ui/button"

export default function BulkPage() {
  return (
    <main className="min-h-screen bg-background">
      <div className="container mx-auto px-4 py-12 max-w-6xl">
        <div className="flex flex-col items-center text-center mb-12 space-y-4">
          <div className="flex items-center justify-center w-16 h-16 rounded-full bg-primary/10 mb-2">
            <FileSpreadsheetIcon className="w-8 h-8 text-primary" />
          </div>
          <h1 className="text-4xl md:text-5xl font-bold tracking-tight text-balance">Bulk Product Scraper</h1>
          <p className="text-lg md:text-xl text-muted-foreground max-w-2xl text-balance">
            Upload an Excel file with multiple products to scrape product information in bulk
          </p>
          <div className="pt-4">
            <Button variant="outline" asChild>
              <Link href="/">← Back to Single Search</Link>
            </Button>
          </div>
        </div>

        <BulkUploadForm />
      </div>
    </main>
  )
}
