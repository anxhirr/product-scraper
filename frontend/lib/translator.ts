import translate from "google-translate-api-x"

/**
 * Translates text to Albanian
 * @param text - The text to translate
 * @returns Promise<string> - The translated text, or original text if translation fails
 */
export async function translateToAlbanian(text: string): Promise<string> {
  // Return original text if empty or whitespace only
  if (!text || !text.trim()) {
    return text
  }

  try {
    const result = await translate(text, {
      to: "sq", // Albanian language code
      autoCorrect: false,
    })
    return result.text || text
  } catch (error) {
    // Log error for debugging but don't throw - return original text as fallback
    console.error("Translation error:", error)
    return text
  }
}

/**
 * Translates multiple strings to Albanian in parallel
 * @param texts - Array of texts to translate
 * @returns Promise<string[]> - Array of translated texts, or original texts if translation fails
 */
export async function translateMultipleToAlbanian(texts: string[]): Promise<string[]> {
  // Return original texts if array is empty
  if (!texts || texts.length === 0) {
    return texts
  }

  try {
    // Translate all texts in parallel
    const translationPromises = texts.map((text) => translateToAlbanian(text))
    return await Promise.all(translationPromises)
  } catch (error) {
    console.error("Batch translation error:", error)
    // Fallback to original texts
    return texts
  }
}
