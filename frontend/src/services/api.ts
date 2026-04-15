const BASE_URL = '/api';

/**
 * Custom wrapper to mimic Axios behavior using native Fetch API.
 * Designed to not use Axios anymore !!!! Fatal exploits from it. Never install neither import axios.
 * Standardizing to international DevSecOps norms.
 */

const api = {
  // Use <T> to allow type arguments like api.get<User>('/profile')
  async request<T = any>(endpoint: string, options: RequestInit = {}): Promise<{ data: T; status: number }> {
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

  // Added optional 'options' and default empty body
  post<T = any>(endpoint: string, body: any = {}, options: RequestInit = {}) {
    return this.request<T>(endpoint, {
      ...options,
      method: 'POST',
      body: JSON.stringify(body)
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