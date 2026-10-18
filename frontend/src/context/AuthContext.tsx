import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { User } from '../types';
import { loginUser, registerUser, getCurrentUser, logoutUser } from '../api/client';

interface AuthContextType {
  user: User | null;
  token: string | null;
  role: 'USER' | 'ADMIN' | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (username: string, password: string) => Promise<User>;
  register: (data: { username: string; email: string; password: string; full_name?: string; department?: string }) => Promise<User>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  useEffect(() => {
    const savedToken = localStorage.getItem('cachemind_token');
    const savedUser = localStorage.getItem('cachemind_user');

    if (savedToken && savedUser) {
      try {
        setToken(savedToken);
        setUser(JSON.parse(savedUser));
        // Verify in background
        getCurrentUser()
          .then((freshUser) => {
            setUser(freshUser);
            localStorage.setItem('cachemind_user', JSON.stringify(freshUser));
          })
          .catch(() => {
            // Token expired or invalid
            logoutUser();
            setUser(null);
            setToken(null);
          })
          .finally(() => setIsLoading(false));
      } catch (e) {
        logoutUser();
        setIsLoading(false);
      }
    } else {
      setIsLoading(false);
    }
  }, []);

  const login = async (username: string, password: string): Promise<User> => {
    setIsLoading(true);
    try {
      const data = await loginUser({ username, password });
      setToken(data.access_token);
      setUser(data.user);
      return data.user;
    } finally {
      setIsLoading(false);
    }
  };

  const register = async (data: {
    username: string;
    email: string;
    password: string;
    full_name?: string;
    department?: string;
  }): Promise<User> => {
    setIsLoading(true);
    try {
      const resp = await registerUser(data);
      setToken(resp.access_token);
      setUser(resp.user);
      return resp.user;
    } finally {
      setIsLoading(false);
    }
  };

  const logout = () => {
    logoutUser();
    setUser(null);
    setToken(null);
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        role: user?.role || null,
        isAuthenticated: !!user,
        isLoading,
        login,
        register,
        logout
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
