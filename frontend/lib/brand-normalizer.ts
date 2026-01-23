/**
 * Normalizes brand names from various display formats to internal format.
 * Maps common variations like "Done by Deer" to "done_by_deer"
 * 
 * @param brand - The brand name in any format (e.g., "Done by Deer", "done by deer", "DoneByDeer")
 * @returns The normalized brand name in internal format (e.g., "done_by_deer") or undefined if brand is empty
 */
export function normalizeBrandName(brand: string | undefined): string | undefined {
  if (!brand) return undefined
  
  const normalized = brand.trim().toLowerCase()
  
  // Map common brand name variations to internal format
  const brandMappings: Record<string, string> = {
    // Done by Deer variations
    "done by deer": "done_by_deer",
    "donebydeer": "done_by_deer",
    "done-by-deer": "done_by_deer",
    "done_by_deer": "done_by_deer",
    // Hape variations
    "hape": "hape",
    "hape global": "hape",
    "hape_global": "hape",
    // Rockahula variations
    "rockahula": "rockahula",
    // Bambino variations
    "bambino": "bambino",
    "bambino by juliana": "bambino",
    "bambino-by-juliana": "bambino",
    // LieWood variations
    "liewood": "liewood",
    "lie wood": "liewood",
    "lie-wood": "liewood",
  }
  
  // Check exact match first
  if (brandMappings[normalized]) {
    return brandMappings[normalized]
  }
  
  // Try to match by replacing spaces/separators with underscores
  const withUnderscores = normalized.replace(/[\s-]+/g, "_")
  if (brandMappings[withUnderscores]) {
    return brandMappings[withUnderscores]
  }
  
  // If no mapping found, return normalized version (backend will validate)
  return withUnderscores
}
