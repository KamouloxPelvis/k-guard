const BASE_URL = '/api';

/**
 * Custom wrapper to mimic Axios behavior using native Fetch API.
 * Designed to not use Axios anymore !!!! Fatal exploits from it. Never install neither import axios.
 * Standardizing to international DevSecOps norms.
 */

const api = {
  async request<T = any>(endpoint: string, options: RequestInit = {}): Promise<{ data: T; status: number }> {
    const token = localStorage.getItem('user_token');
    const headers = new Headers(options.headers);
    
    // Si le Content-Type n'est pas déjà défini dans les options, on met JSON par défaut
    if (!headers.has('Content-Type')) {
      headers.set('Content-Type', 'application/json');
    }

    if (token) {
      headers.set('Authorization', `Bearer ${token}`);
    }

    const config: RequestInit = {
      ...options,
      headers
    };

    try {
      const response = await fetch(`${BASE_URL}${endpoint}`, config);

      if (!response.ok) {
        if (response.status === 401) {
          console.warn("🔒 Session invalid or expired, cleaning up...");
          localStorage.removeItem('user_token');
          if (!window.location.pathname.endsWith('/login')) {
            window.location.href = '/login';
          }
        }

        const errorData = await response.json().catch(() => ({}));
        throw { response: { status: response.status, data: errorData } };
      }

      const data = await response.json();
      return { data, status: response.status };
    } catch (error) {
      throw error;
    }
  },

  // Added optional 'options' to match expected 2 arguments in some views
  get<T = any>(endpoint: string, options: RequestInit = {}) {
    return this.request<T>(endpoint, { ...options, method: 'GET' });
  },

  /**
   * Sends a POST request to the API.
   * Handles both JSON and URLSearchParams (OAuth2) payloads.
   */
  post<T = any>(endpoint: string, body: any = {}, options: RequestInit = {}) {
    const headers = new Headers(options.headers);
    const contentType = headers.get('Content-Type');

    let finalBody;
    
    // Check if the request expects form-urlencoded data (for OAuth2 authentication)
    if (contentType === 'application/x-www-form-urlencoded') {
      finalBody = body; // Pass URLSearchParams directly to fetch
    } else {
      finalBody = JSON.stringify(body); // Default to JSON serialization
    }

    return this.request<T>(endpoint, {
      ...options,
      method: 'POST',
      body: finalBody
    });
  },

  put<T = any>(endpoint: string, body: any = {}, options: RequestInit = {}) {
    return this.request<T>(endpoint, {
      ...options,
      method: 'PUT',
      body: JSON.stringify(body)
    });
  },

  delete<T = any>(endpoint: string, options: RequestInit = {}) {
    return this.request<T>(endpoint, { ...options, method: 'DELETE' });
  }
};

export default api;