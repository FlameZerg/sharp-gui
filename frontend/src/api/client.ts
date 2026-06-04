/**
 * Base API client with error handling
 */

export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
    public data?: ApiErrorData | null
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

export interface ApiErrorData {
  error?: string;
  code?: string;
  [key: string]: unknown;
}

interface FetchOptions extends RequestInit {
  timeout?: number;
}

async function fetchWithTimeout(
  url: string,
  options: FetchOptions = {}
): Promise<Response> {
  const { timeout = 30000, ...fetchOptions } = options;

  const controller = new AbortController();
  const id = setTimeout(() => controller.abort(), timeout);

  try {
    const response = await fetch(url, {
      credentials: fetchOptions.credentials ?? 'same-origin',
      ...fetchOptions,
      signal: controller.signal,
    });
    return response;
  } finally {
    clearTimeout(id);
  }
}

async function readErrorData(response: Response): Promise<ApiErrorData | null> {
  const errorData = await response.json().catch(() => null);
  return errorData && typeof errorData === 'object' ? errorData as ApiErrorData : null;
}

async function throwApiError(response: Response): Promise<never> {
  const errorData = await readErrorData(response);
  throw new ApiError(
    errorData?.error || `HTTP error! status: ${response.status}`,
    response.status,
    errorData
  );
}

export async function apiGet<T>(url: string): Promise<T> {
  const response = await fetchWithTimeout(url);
  
  if (!response.ok) {
    await throwApiError(response);
  }
  
  return response.json();
}

export async function apiPost<T>(
  url: string,
  data?: unknown,
  options?: RequestInit & { timeout?: number }
): Promise<T> {
  const response = await fetchWithTimeout(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
    body: data ? JSON.stringify(data) : undefined,
    ...options,
  });
  
  if (!response.ok) {
    await throwApiError(response);
  }
  
  return response.json();
}

export async function apiPostBlob(
  url: string,
  data?: unknown,
  options?: RequestInit & { timeout?: number }
): Promise<{ blob: Blob; response: Response }> {
  const { headers, ...restOptions } = options ?? {};
  const response = await fetchWithTimeout(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...headers,
    },
    body: data ? JSON.stringify(data) : undefined,
    ...restOptions,
  });

  if (!response.ok) {
    await throwApiError(response);
  }

  return {
    blob: await response.blob(),
    response,
  };
}

export async function apiPostFormData<T>(
  url: string,
  formData: FormData,
  options?: RequestInit & { timeout?: number }
): Promise<T> {
  const { headers, ...restOptions } = options ?? {};
  const response = await fetchWithTimeout(url, {
    method: 'POST',
    body: formData,
    headers,
    ...restOptions,
  });
  
  if (!response.ok) {
    await throwApiError(response);
  }
  
  return response.json();
}

export async function apiDelete<T>(url: string): Promise<T> {
  const response = await fetchWithTimeout(url, {
    method: 'DELETE',
  });
  
  if (!response.ok) {
    await throwApiError(response);
  }
  
  return response.json();
}
