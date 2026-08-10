import { Navigate, useLocation } from 'react-router-dom';

/**
 * Route guard: redirect unauthenticated users to /login.
 * JWT is stored in localStorage by api/client.login().
 */
export function RequireAuth({ children }) {
  const location = useLocation();
  const token = localStorage.getItem('meridian_access_token');
  if (!token) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  }
  return children;
}

export function isAuthenticated() {
  return Boolean(localStorage.getItem('meridian_access_token'));
}
