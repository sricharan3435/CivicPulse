import { createContext, useContext, useEffect, useState } from 'react';

const AuthContext = createContext(null);

async function authRequest(path, options = {}) {
  const response = await fetch(`/api/auth${path}`, {
    ...options,
    headers: { ...(options.body ? { 'Content-Type': 'application/json' } : {}), ...(options.headers || {}) },
  });
  const data = response.status === 204 ? null : await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data?.detail || `Request failed (${response.status})`);
  return data;
}

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    authRequest('/me').then((data) => setUser(data.user)).catch(() => setUser(null)).finally(() => setLoading(false));
  }, []);

  async function signIn(email, password) {
    const nextUser = await authRequest('/login', { method: 'POST', body: JSON.stringify({ email, password }) });
    setUser(nextUser);
    return nextUser;
  }

  async function signInAsAdmin(email, password) {
    const nextUser = await authRequest('/admin-login', { method: 'POST', body: JSON.stringify({ email, password }) });
    setUser(nextUser);
    return nextUser;
  }

  async function signUp(full_name, email, password) {
    const nextUser = await authRequest('/signup', { method: 'POST', body: JSON.stringify({ full_name, email, password }) });
    setUser(nextUser);
    return nextUser;
  }

  async function signOut() {
    try { await authRequest('/logout', { method: 'POST' }); }
    finally { setUser(null); }
  }

  return <AuthContext.Provider value={{ user, loading, signIn, signInAsAdmin, signUp, signOut }}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const value = useContext(AuthContext);
  if (!value) throw new Error('useAuth must be used inside AuthProvider');
  return value;
}
