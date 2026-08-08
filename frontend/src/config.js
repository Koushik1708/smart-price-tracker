import axios from 'axios';

export const API_BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8001";

// Handle global 401 errors for expired tokens
axios.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response && error.response.status === 401) {
      sessionStorage.removeItem('jwtToken');
      // Redirect to login if not already there
      if (window.location.pathname !== '/login' && window.location.pathname !== '/register') {
        window.location.href = '/login';
      }
    }
    return Promise.reject(error);
  }
);
