const BASE_URL = '/api';

/**
 * Custom wrapper to mimic Axios behavior using native Fetch API.
 * Designed to not use Axios anymore !!!! Fatal exploits from it. Never install neither import axios.
 * Fetch is back...
 */

const api = {
  async request(endpoint: string, options: RequestInit = {}) {
    // --- REQUEST INTERCEPTOR LOGIC ---
    const token = localStorage.getItem('user_token');
    const headers = new Headers(options.headers);
    
    headers.set('Content-Type', 'application/json');
    if (token) {
      headers.set('Authorization', `Bearer ${token}`);
    }

    const config: RequestInit = {
      ...options,
      headers
    };

    try {
      const response = await fetch(`${BASE_URL}${endpoint}`, config);

      // --- RESPONSE INTERCEPTOR LOGIC ---
      if (!response.ok) {
        // Handle 401 Unauthorized (Expired or invalid session)
        if (response.status === 401) {
          console.warn("🔒 Session invalid or expired, cleaning up...");
          localStorage.removeItem('user_token');
          
          if (!window.location.pathname.endsWith('/login')) {
            window.location.href = '/login';
          }
        }

        // Extract error details to match Axios error structure
        const errorData = await response.json().catch(() => ({}));
        throw { response: { status: response.status, data: errorData } };
      }

      // Return data wrapped in an object to maintain compatibility with existing components
      const data = await response.json();
      return { data };
    } catch (error) {
      throw error;
    }
  },

  get(endpoint: string) {
    return this.request(endpoint, { method: 'GET' });
  },

  post(endpoint: string, body: any) {
    return this.request(endpoint, {
      method: 'POST',
      body: JSON.stringify(body)
    });
  },

  put(endpoint: string, body: any) {
    return this.request(endpoint, {
      method: 'PUT',
      body: JSON.stringify(body)
    });
  },

  delete(endpoint: string) {
    return this.request(endpoint, { method: 'DELETE' });
  }
};

export default api;