import React, { createContext, useState, useEffect } from 'react';
import axios from 'axios';
import { API_BASE_URL } from './config';

export const AuthContext = createContext();

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(sessionStorage.getItem('jwtToken'));
  const [loading, setLoading] = useState(true);



  const fetchCurrentUser = async (currentToken = token) => {
    const activeToken = currentToken || token;
    if (!activeToken) {
      setUser(null);
      setLoading(false);
      return null;
    }
    setLoading(true);
    try {
      axios.defaults.headers.common['Authorization'] = `Bearer ${activeToken}`;
      const response = await axios.get(`${API_BASE_URL}/auth/me`);
      setUser(response.data);
      return response.data;
    } catch (error) {
      console.error("Failed to fetch user", error);
      sessionStorage.removeItem('jwtToken');
      delete axios.defaults.headers.common['Authorization'];
      setToken(null);
      setUser(null);
      return null;
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (token) {
      sessionStorage.setItem('jwtToken', token);
      fetchCurrentUser(token);
    } else {
      sessionStorage.removeItem('jwtToken');
      delete axios.defaults.headers.common['Authorization'];
      setUser(null);
      setLoading(false);
    }
  }, [token]);

  const login = async (email, password) => {
    const formData = new URLSearchParams();
    formData.append('username', email ? email.trim() : ''); // OAuth2 expects 'username'
    formData.append('password', password);
    
    const response = await axios.post(`${API_BASE_URL}/auth/login`, formData, {
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded'
      }
    });
    const newToken = response.data.access_token;
    sessionStorage.setItem('jwtToken', newToken);
    axios.defaults.headers.common['Authorization'] = `Bearer ${newToken}`;
    setToken(newToken);
    await fetchCurrentUser(newToken);
  };

  const register = async (name, email, password) => {
    await axios.post(`${API_BASE_URL}/auth/register`, { name, email, password });
    await login(email, password); // auto-login after register
  };

  const logout = () => {
    setToken(null);
  };

  return (
    <AuthContext.Provider value={{ user, token, loading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
};
