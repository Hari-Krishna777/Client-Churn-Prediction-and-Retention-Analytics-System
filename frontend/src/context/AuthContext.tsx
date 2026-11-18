import React, { createContext, useContext, useState, useEffect } from 'react';
import { User } from '../types';
import { authApi } from '../api/auth';

interface AuthContextType {
  user: User | null;
  loading: boolean;
  login: (username: string, password: string) => Promise<void>;
  register: (username: string, email: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(() => Boolean(localStorage.getItem('churniq_token')));

  useEffect(() => {
    let active = true;
    const token = localStorage.getItem('churniq_token');

    if (!token) {
      return () => {
        active = false;
      };
    }

    authApi
      .getCurrentUser()
      .then((data) => {
        if (!active) return;
        const { access_token: accessToken, ...authenticatedUser } = data;
        setUser(authenticatedUser);
        localStorage.setItem('churniq_token', accessToken);
      })
      .catch(() => {
        localStorage.removeItem('churniq_token');
      })
      .finally(() => {
        if (active) setLoading(false);
      });

    return () => {
      active = false;
    };
  }, []);

  const establishSession = (accessToken: string, authenticatedUser: User) => {
    localStorage.setItem('churniq_token', accessToken);
    setUser(authenticatedUser);
  };

  const login = async (username: string, password: string) => {
    const { access_token: accessToken, ...authenticatedUser } = await authApi.login(username, password);
    establishSession(accessToken, authenticatedUser);
  };

  const register = async (username: string, email: string, password: string) => {
    const { access_token: accessToken, ...authenticatedUser } = await authApi.register(username, email, password);
    establishSession(accessToken, authenticatedUser);
  };

  const logout = () => {
    setUser(null);
    localStorage.removeItem('churniq_token');
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout }}>
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
