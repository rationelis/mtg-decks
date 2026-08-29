/** Must match scripts/build/parse.py's normalize_name exactly, so client-side
 * lookups into cards.json (keyed by normalized name) line up with names as
 * typed in bulk/deck files. */
export function normalizeName(name: string): string {
  return name.normalize("NFC").trim().toLowerCase();
}
