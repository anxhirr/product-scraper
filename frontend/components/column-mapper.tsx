"use client"

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Label } from "@/components/ui/label"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { AlertCircleIcon } from "lucide-react"

interface ColumnMapperProps {
  columns: string[]
  mapping: {
    name?: string
    code?: string
    brand?: string
  }
  onMappingChange: (mapping: {
    name?: string
    code?: string
    brand?: string
  }) => void
}

export default function ColumnMapper({
  columns,
  mapping,
  onMappingChange,
}: ColumnMapperProps) {
  const handleChange = (field: "name" | "code" | "brand", value: string) => {
    const newMapping = { ...mapping }
    if (value === "skip") {
      delete newMapping[field]
    } else {
      newMapping[field] = value
    }
    onMappingChange(newMapping)
  }

  const isNameOrCodeMapped = mapping.name || mapping.code
  const isBrandMapped = mapping.brand

  // Check which fields are auto-detected (have a mapping)
  const autoDetectedFields = {
    name: !!mapping.name,
    code: !!mapping.code,
    brand: !!mapping.brand,
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Map Columns</CardTitle>
        <CardDescription>
          Map Excel columns to product fields. At least one of Name or Code is required, and Brand
          is required. {Object.values(autoDetectedFields).some(v => v) && "Some columns have been auto-detected."}
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="map-name">
                Product Name {!mapping.name && !mapping.code && (
                  <span className="text-destructive">*</span>
                )}
                {autoDetectedFields.name && (
                  <span className="text-xs text-muted-foreground ml-2">(auto-detected)</span>
                )}
              </Label>
              <Select
                value={mapping.name || "skip"}
                onValueChange={(value) => handleChange("name", value)}
              >
                <SelectTrigger id="map-name">
                  <SelectValue placeholder="Select column" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="skip">Skip</SelectItem>
                  {columns.map((col) => (
                    <SelectItem key={col} value={col}>
                      {col}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label htmlFor="map-code">
                Product Code/SKU {!mapping.name && !mapping.code && (
                  <span className="text-destructive">*</span>
                )}
                {autoDetectedFields.code && (
                  <span className="text-xs text-muted-foreground ml-2">(auto-detected)</span>
                )}
              </Label>
              <Select
                value={mapping.code || "skip"}
                onValueChange={(value) => handleChange("code", value)}
              >
                <SelectTrigger id="map-code">
                  <SelectValue placeholder="Select column" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="skip">Skip</SelectItem>
                  {columns.map((col) => (
                    <SelectItem key={col} value={col}>
                      {col}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label htmlFor="map-brand">
                Brand <span className="text-destructive">*</span>
                {autoDetectedFields.brand && (
                  <span className="text-xs text-muted-foreground ml-2">(auto-detected)</span>
                )}
              </Label>
              <Select
                value={mapping.brand || "skip"}
                onValueChange={(value) => handleChange("brand", value)}
              >
                <SelectTrigger id="map-brand">
                  <SelectValue placeholder="Select column" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="skip">Skip</SelectItem>
                  {columns.map((col) => (
                    <SelectItem key={col} value={col}>
                      {col}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          {/* Validation Messages */}
          {(!isNameOrCodeMapped || !isBrandMapped) && (
            <div className="flex items-start gap-2 p-3 bg-destructive/10 border border-destructive/20 rounded-md">
              <AlertCircleIcon className="w-4 h-4 text-destructive mt-0.5" />
              <div className="text-sm text-destructive">
                {!isBrandMapped && "Please map the 'Brand' column. "}
                {!isNameOrCodeMapped &&
                  "Please map either 'Product Name' or 'Product Code' column."}
              </div>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  )
}
