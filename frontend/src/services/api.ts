import axios from 'axios';

const api = axios.create({
  baseURL: '/api'
});

// --- INTERCEPTEUR DE REQUÊTE ---
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('user_token');
    if (token) {
      // Aligné sur le backend FastAPI (OAuth2)
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// --- INTERCEPTEUR DE RÉPONSE ---
api.interceptors.response.use(
  (response) => response,
  (error) => {

    if (error.response && error.response.status === 401) {
      console.warn("🔒 Session invalide ou expirée, redirection...");
      localStorage.removeItem('user_token');
      
      if (!window.location.pathname.endsWith('/login')) {
      window.location.href = '/login';
      }
    }
    return Promise.reject(error);
  }
);

export default api;