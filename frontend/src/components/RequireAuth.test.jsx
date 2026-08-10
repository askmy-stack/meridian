import { describe, expect, it, beforeEach } from 'vitest';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { render, screen } from '@testing-library/react';
import { RequireAuth } from './RequireAuth';

function renderWithAuth(initialPath = '/alerts') {
  return render(
    <MemoryRouter initialEntries={[initialPath]}>
      <Routes>
        <Route
          path="/alerts"
          element={
            <RequireAuth>
              <div>Secret alerts</div>
            </RequireAuth>
          }
        />
        <Route path="/login" element={<div>Login page</div>} />
      </Routes>
    </MemoryRouter>
  );
}

describe('RequireAuth', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('redirects to login when token missing', () => {
    renderWithAuth();
    expect(screen.getByText('Login page')).toBeTruthy();
  });

  it('renders children when token present', () => {
    localStorage.setItem('meridian_access_token', 'test-jwt');
    renderWithAuth();
    expect(screen.getByText('Secret alerts')).toBeTruthy();
  });
});
