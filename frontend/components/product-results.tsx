import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { ExternalLinkIcon, ImageIcon, FileTextIcon, ListIcon } from "lucide-react"
import type { ProductData } from "./product-scraper-form"

interface ProductResultsProps {
  data: ProductData
}

export default function ProductResults({ data }: ProductResultsProps) {
  return (
    <div className="space-y-6 animate-in fade-in-50 duration-500">
      <Card>
        <CardHeader>
          <div className="flex items-start justify-between">
            <div>
              <CardTitle className="text-2xl">{data.name}</CardTitle>
              <CardDescription className="mt-2">
                {data.brand} · {data.code}
              </CardDescription>
            </div>
            {data.sourceUrl && (
              <a
                href={data.sourceUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="text-sm text-muted-foreground hover:text-foreground flex items-center gap-1"
              >
                View Source
                <ExternalLinkIcon className="w-4 h-4" />
              </a>
            )}
          </div>
        </CardHeader>
      </Card>

      {data.description && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <FileTextIcon className="w-5 h-5" />
              Description
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-foreground leading-relaxed">{data.description}</p>
          </CardContent>
        </Card>
      )}

      {data.specifications && Object.keys(data.specifications).length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <ListIcon className="w-5 h-5" />
              Specifications
            </CardTitle>
          </CardHeader>
          <CardContent>
            <dl className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {Object.entries(data.specifications).map(([key, value]) => (
                <div key={key} className="space-y-1">
                  <dt className="text-sm font-medium text-muted-foreground">{key}</dt>
                  <dd className="text-sm text-foreground">{value}</dd>
                </div>
              ))}
            </dl>
          </CardContent>
        </Card>
      )}

      {data.images && data.images.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <ImageIcon className="w-5 h-5" />
              Product Images
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
              {data.images.map((image, index) => (
                <div key={index} className="aspect-square rounded-lg overflow-hidden border bg-muted">
                  <img
                    src={image || "/placeholder.svg"}
                    alt={`${data.name} - Image ${index + 1}`}
                    className="w-full h-full object-cover hover:scale-105 transition-transform duration-300"
                  />
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
