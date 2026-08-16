function localStorageOrNull(): Storage | null {
  if (typeof window === 'undefined') return null

  try {
    return window.localStorage
  } catch {
    return null
  }
}

export function readLocalPreference(key: string): string | null {
  try {
    return localStorageOrNull()?.getItem(key) ?? null
  } catch {
    return null
  }
}

export function writeLocalPreference(key: string, value: string): boolean {
  try {
    const storage = localStorageOrNull()
    if (!storage) return false
    storage.setItem(key, value)
    return true
  } catch {
    return false
  }
}

export function removeLocalPreference(key: string): boolean {
  try {
    const storage = localStorageOrNull()
    if (!storage) return false
    storage.removeItem(key)
    return true
  } catch {
    return false
  }
}
