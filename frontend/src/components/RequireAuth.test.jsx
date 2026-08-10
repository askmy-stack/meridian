import { describe, expect, it, beforeEach, vi } from 'vitest';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { render, screen } from '@testing-library/react';
import { RequireAuth } from './RequireAuth';

const store = new Map();
const localStorageMock = {
  getItem: (k) => (store.has(k) ? store.get(k) : null),
  setItem: (k, v) => store.set(k, String(v)),
  removeItem: (k) => store.delete(k),
  clear: () => store.clear(),
};
vi.stubGlobal('localStorage', localStorageMock);

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
    store.clear();
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
