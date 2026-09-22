/**
 * Official friendly display names for Nintendo 3DS family hardware models.
 */
export const DEVICE_MODEL_NAMES: Record<string, string> = {
  "3ds": "Nintendo 3DS",
  "3ds_xl": "Nintendo 3DS XL",
  "new_3ds": "New Nintendo 3DS",
  "new_3ds_xl": "New Nintendo 3DS XL",
  "2ds": "Nintendo 2DS",
  "new_2ds_xl": "New Nintendo 2DS XL",
  "new3dsxl": "New Nintendo 3DS XL",
};

/**
 * Formats a device model identifier or raw name into a clean, human-friendly title.
 */
export function formatDeviceName(name?: string): string {
  if (!name || !name.trim()) {
    return "Nintendo 3DS";
  }
  const clean = name.trim();
  const normalized = clean.toLowerCase();
  return DEVICE_MODEL_NAMES[normalized] ?? clean;
}
