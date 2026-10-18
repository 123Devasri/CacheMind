import React from 'react';
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { AuthPage } from '../pages/AuthPage';
import { AuthProvider } from '../context/AuthContext';

describe('AuthPage UI Component', () => {
  it('renders single sign-in form without demo buttons or create account tab', () => {
    render(
      <AuthProvider>
        <BrowserRouter>
          <AuthPage />
        </BrowserRouter>
      </AuthProvider>
    );

    // Checks presence of brand and unified sign in form
    expect(screen.getByText(/Governed Semantic Cache/i)).toBeTruthy();
    expect(screen.getByText(/Enterprise Sign In/i)).toBeTruthy();
    expect(screen.getByPlaceholderText(/admin or user/i)).toBeTruthy();
    expect(screen.getByRole('button', { name: /Sign In/i })).toBeTruthy();
    
    // Confirms demo buttons and create account are absent
    expect(screen.queryByText(/Instant Demo Evaluation/i)).toBeNull();
    expect(screen.queryByText(/Create Account/i)).toBeNull();
  });
});
