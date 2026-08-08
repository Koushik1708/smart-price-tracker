import axios from 'axios';
import { API_BASE_URL } from './config';

// Create a centralized Axios instance
const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000, // 10 seconds global timeout
  withCredentials: true
});

// Request Interceptor to dynamically inject the JWT token
apiClient.interceptors.request.use(
  (config) => {
    const token = sessionStorage.getItem('jwtToken');
    if (token) {
      config.headers['Authorization'] = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response Interceptor for centralized error handling
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    // If request was cancelled, just reject it silently
    if (axios.isCancel(error)) {
      return Promise.reject(error);
    }

    let customErrorMessage = 'An unexpected error occurred.';
    let errorType = 'error'; // can be 'network', 'timeout', etc.

    if (error.code === 'ECONNABORTED' || error.message.includes('timeout')) {
      customErrorMessage = 'Request timed out. Please retry.';
      errorType = 'timeout';
    } else if (!error.response) {
      // Network Error or Backend Unavailable
      customErrorMessage = "Cannot connect to backend. Verify: FastAPI server is running, Redis is running, Celery worker is running.";
      errorType = 'network';
    } else {
      // Backend returned an error response
      const status = error.response.status;
      const detail = error.response.data?.detail || error.response.data?.message;
      
      if (status === 401 || status === 403) {
        customErrorMessage = detail || 'Unauthorized access.';
        errorType = 'unauthorized';
      } else if (status === 400 || status === 422) {
        customErrorMessage = detail || 'Validation error.';
        errorType = 'validation';
      } else if (status === 409) {
        customErrorMessage = detail || 'Item already exists.';
        errorType = 'conflict';
      } else {
        customErrorMessage = detail || `Server Error (${status})`;
        errorType = 'server';
      }
    }

    // Attach structured error info for components to use
    error.customMessage = customErrorMessage;
    error.customType = errorType;

    return Promise.reject(error);
  }
);

export default apiClient;
