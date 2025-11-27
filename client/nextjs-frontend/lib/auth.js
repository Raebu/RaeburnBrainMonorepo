import { createContext, useContext, useEffect, useState, useCallback } from 'react';
import Router from 'next/router';
import cookies from 'js-cookie';

const AuthContext = createContext();

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [token, setToken] = useState(null);

  const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:3001';

  // Check for existing session on app load
  useEffect(() => {
    const initializeAuth = async () => {
      const storedToken = cookies.get('token');
      if (storedToken) {
        setToken(storedToken);
        try {
          const response = await fetch(`${API_URL}/api/users/me`, {
            headers: {
              'Authorization': `Bearer ${storedToken}`
            }
          });
          
          if (response.ok) {
            const userData = await response.json();
            setUser(userData);
          } else {
            // Token invalid, clear it
            cookies.remove('token');
            setToken(null);
          }
        } catch (error) {
          console.error('Auth check failed:', error);
          cookies.remove('token');
          setToken(null);
        }
      }
      setLoading(false);
    };

    initializeAuth();
  }, [API_URL]);

  const login = useCallback(async (email, password) => {
    try {
      const response = await fetch(`${API_URL}/api/auth/login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ email, password })
      });

      const data = await response.json();

      if (response.ok) {
        cookies.set('token', data.token, { expires: 7 }); // 7 days
        setToken(data.token);
        setUser(data.user);
        Router.push('/dashboard');
        return { success: true };
      } else {
        return { success: false, error: data.error || 'Login failed' };
      }
    } catch (error) {
      console.error('Login error:', error);
      return { success: false, error: 'Network error' };
    }
  }, [API_URL]);

  const signup = useCallback(async (name, email, password) => {
    try {
      const response = await fetch(`${API_URL}/api/auth/signup`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ name, email, password })
      });

      const data = await response.json();

      if (response.ok) {
        cookies.set('token', data.token, { expires: 7 });
        setToken(data.token);
        setUser(data.user);
        Router.push('/onboarding'); // Redirect to onboarding after signup
        return { success: true };
      } else {
        return { success: false, error: data.error || 'Signup failed' };
      }
    } catch (error) {
      console.error('Signup error:', error);
      return { success: false, error: 'Network error' };
    }
  }, [API_URL]);

  const logout = useCallback(() => {
    cookies.remove('token');
    setToken(null);
    setUser(null);
    Router.push('/login');
  }, []);

  const googleLogin = useCallback(() => {
    // Redirect to Google OAuth endpoint
    window.location.href = `${API_URL}/api/auth/google`;
  }, [API_URL]);

  const updateProfile = useCallback(async (userData) => {
    if (!token) return { success: false, error: 'Not authenticated' };

    try {
      const response = await fetch(`${API_URL}/api/users/profile`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify(userData)
      });

      const data = await response.json();

      if (response.ok) {
        setUser(prev => ({ ...prev, ...data }));
        return { success: true, user: data };
      } else {
        return { success: false, error: data.error || 'Update failed' };
      }
    } catch (error) {
      console.error('Profile update error:', error);
      return { success: false, error: 'Network error' };
    }
  }, [API_URL, token]);

  const addSession = useCallback(async (sessionData) => {
    if (!token) return { success: false, error: 'Not authenticated' };

    try {
      const response = await fetch(`${API_URL}/api/users/sessions`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify(sessionData)
      });

      const data = await response.json();

      if (response.ok) {
        setUser(prev => ({
          ...prev,
          sessions: [...(prev.sessions || []), data]
        }));
        return { success: true, session: data };
      } else {
        return { success: false, error: data.error || 'Failed to add session' };
      }
    } catch (error) {
      console.error('Add session error:', error);
      return { success: false, error: 'Network error' };
    }
  }, [API_URL, token]);

  const deleteSession = useCallback(async (sessionId) => {
    if (!token) return { success: false, error: 'Not authenticated' };

    try {
      const response = await fetch(`${API_URL}/api/users/sessions/${sessionId}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      if (response.ok) {
        setUser(prev => ({
          ...prev,
          sessions: (prev.sessions || []).filter(s => s.id !== sessionId)
        }));
        return { success: true };
      } else {
        const data = await response.json();
        return { success: false, error: data.error || 'Failed to delete session' };
      }
    } catch (error) {
      console.error('Delete session error:', error);
      return { success: false, error: 'Network error' };
    }
  }, [API_URL, token]);

  const value = {
    user,
    loading,
    token,
    login,
    signup,
    logout,
    googleLogin,
    updateProfile,
    addSession,
    deleteSession,
    isAuthenticated: !!user
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  
  return context;
}

// Higher-order component for protected routes
export function withAuth(Component) {
  return function ProtectedRoute(props) {
    const { isAuthenticated, loading } = useAuth();
    const router = Router.useRouter();

    useEffect(() => {
      if (!loading && !isAuthenticated) {
        router.push('/login');
      }
    }, [isAuthenticated, loading, router]);

    if (loading || !isAuthenticated) {
      return <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-gray-900"></div>
      </div>;
    }

    return <Component {...props} />;
  };
}

// Hook for checking if user has specific permissions
export function usePermissions() {
  const { user } = useAuth();
  
  const hasPermission = (permission) => {
    if (!user || !user.permissions) return false;
    return user.permissions.includes(permission);
  };
  
  const isProUser = () => {
    return user && user.plan === 'pro';
  };
  
  const canScrape = () => {
    if (!user) return false;
    return user.quota && user.quota.usedToday < user.quota.dailyLimit;
  };
  
  return {
    hasPermission,
    isProUser,
    canScrape
  };
}
