import axios from 'axios';

const api = axios.create({
  // Base URL pointing to the FastAPI backend proxy or ingress
  baseURL: '/api'
});

// --- REQUEST INTERCEPTOR ---
api.interceptors.request.use(
  (config) => {
    // Retrieve the JWT token from browser local storage
    const token = localStorage.getItem('user_token');
    
    if (token) {
      // Aligned with FastAPI OAuth2 / Bearer Token security requirements
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// --- RESPONSE INTERCEPTOR ---
api.interceptors.response.use(
  (response) => response,
  (error) => {
    // Global error handling for unauthorized access
    if (error.response && error.response.status === 401) {
      console.warn("🔒 Session invalid or expired, redirecting to login...");
      
      // Clear credentials from storage to prevent infinite loops
      localStorage.removeItem('user_token');
      
      // Redirect to login page if the user is not already there
      if (!window.location.pathname.endsWith('/login')) {
        window.location.href = '/login';
      }
    }
    return Promise.reject(error);
  }
);

export default api;