const API_URL = process.env.NEXT_PUBLIC_FASTAPI_URL || "http://localhost:8000"

/**
 * Reads or creates a persistent `uid` in localStorage and returns it.
 * Safe to call in browser-only code. If called on the server, returns null.
 */
function getOrCreateUid(): string | null {
  if (typeof window === "undefined" || !window.localStorage) return null
  try {
    let uid = window.localStorage.getItem("uid")
    if (!uid) {
      // crypto.randomUUID is available in modern browsers
      let newUid: string
      if (typeof crypto !== "undefined" && typeof (crypto as any).randomUUID === "function") {
        newUid = (crypto as any).randomUUID()
      } else {
        // Fallback: simple random string (should be rare in modern browsers)
        newUid = Math.random().toString(36).slice(2) + Date.now().toString(36)
      }
      window.localStorage.setItem("uid", newUid)
      uid = newUid
    }
    return uid
  } catch (e) {
    console.warn("Failed to access localStorage for uid", e)
    return null
  }
}

function buildHeaders(extra: Record<string, string> = {}) {
  const headers: Record<string, string> = { ...extra }
  const uid = getOrCreateUid()
  if (uid) headers["X-User-ID"] = uid
  return headers
}

interface ApiResponse<T> {
  success: boolean
  data?: T
  error?: string
}

// 1. UPLOAD COVER IMAGE -> backend /api/input/image
export async function uploadCoverImage(file: File): Promise<ApiResponse<any>> {
  try {
    const formData = new FormData()
    // backend expects field name 'image'
    formData.append("image", file)

    const response = await fetch(`${API_URL}/api/input/image`, {
      method: "POST",
      // don't set content-type for FormData
      headers: buildHeaders(),
      body: formData,
    })

    if (!response.ok) throw new Error("Failed to upload cover")
    const data = await response.json()
    return { success: true, data }
  } catch (error) {
    return { success: false, error: String(error) }
  }
}

// 2. GET BOOKS FROM STORE -> backend /api/store/books
export async function getBookDatabase(): Promise<ApiResponse<Array<any>>> {
  try {
    const response = await fetch(`${API_URL}/api/store/books`, {
      method: "GET",
      headers: buildHeaders(),
    })

    if (!response.ok) throw new Error("Failed to fetch database")
    const data = await response.json()
    return { success: true, data }
  } catch (error) {
    return { success: false, error: String(error) }
  }
}

// 3. SEARCH BOOKS BY TITLE/AUTHOR -> optional: backend supports client-side filtering, so we keep simple
export async function searchBooks(query: string): Promise<ApiResponse<Array<any>>> {
  try {
    // For now, we reuse the store/books endpoint and let frontend filter
    const res = await getBookDatabase()
    if (!res.success) return res
    const q = query.toLowerCase()
    const filtered = (res.data || []).filter((b: any) => {
      return (
        (b.title || "").toLowerCase().includes(q) || (b.authors || "").toLowerCase().includes(q)
      )
    })
    return { success: true, data: filtered }
  } catch (error) {
    return { success: false, error: String(error) }
  }
}

// 4. Select book by ISBN (store selection) -> backend /api/input/store
export async function selectBookByIsbn(isbn: string): Promise<ApiResponse<any>> {
  try {
    const response = await fetch(`${API_URL}/api/input/store`, {
      method: "POST",
      headers: buildHeaders({ "Content-Type": "application/json" }),
      body: JSON.stringify({ isbn }),
    })
    if (!response.ok) throw new Error("Failed to select book")
    const data = await response.json()
    return { success: true, data }
  } catch (error) {
    return { success: false, error: String(error) }
  }
}

// 5. SUBMIT SELF-ENTERED METADATA -> backend /api/input/self
export async function submitMetadata(payload: { title: string; author: string }): Promise<ApiResponse<any>> {
  try {
    const response = await fetch(`${API_URL}/api/input/self`, {
      method: "POST",
      headers: buildHeaders({ "Content-Type": "application/json" }),
      body: JSON.stringify(payload),
    })
    if (!response.ok) {
      const text = await response.text()
      throw new Error(`Failed to submit metadata: ${response.status} ${text}`)
    }
    const data = await response.json()
    return { success: true, data }
  } catch (error) {
    return { success: false, error: String(error) }
  }
}

export async function analyzeShelfImage(
  file: File,
  options: { signal?: AbortSignal } = {}
): Promise<ApiResponse<any>> {
  try {
    const formData = new FormData();
    formData.append("image", file);

    const response = await fetch(`${API_URL}/api/image_upload/image`, {
      method: "POST",
      headers: buildHeaders(),
      body: formData,
      signal: options.signal,
    });

    if (!response.ok) {
      const text = await response.text();
      throw new Error(`Failed to analyze shelf image: ${response.status} ${text}`);
    }

    const data = await response.json();
    return { success: true, data };
  } catch (error) {
    // If aborted, you can detect and silently ignore it if you want
    if ((error as any).name === "AbortError") {
      console.warn("analyzeShelfImage request aborted");
      return { success: false, error: "Request aborted" };
    }
    return { success: false, error: String(error) };
  }
}

// 7. REQUEST RECOMMENDER -> backend /api/image_upload/recommender
export async function getRecommenderResults(
  options: { signal?: AbortSignal; recomData?: any } = {}
): Promise<ApiResponse<any>> {
  try {
    // Add this line to check what you’re sending:
    console.log("Sending recommender payload:", options.recomData);

    const response = await fetch(`${API_URL}/api/image_upload/recommender`, {
      method: "POST",
      headers: buildHeaders({ "Content-Type": "application/json" }),
      body: JSON.stringify(options.recomData || {}),
      signal: options.signal,
    });

    if (!response.ok) {
      const text = await response.text();
      throw new Error(`Failed to get recommender results: ${response.status} ${text}`);
    }

    const data = await response.json();
    return { success: true, data };
  } catch (error) {
    if ((error as any).name === "AbortError") {
      console.warn("getRecommenderResults request aborted");
      return { success: false, error: "Request aborted" };
    }
    return { success: false, error: String(error) };
  }
}

