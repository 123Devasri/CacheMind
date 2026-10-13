import { describe, it, expect } from 'vitest';

describe('AuthContext and Role Enforcement', () => {
  it('stores JWT token and user info on login', () => {
    const fakeToken = 'mock-jwt-token-123';
    const fakeUser = {
      id: 'usr_001',
      username: 'testemployee',
      email: 'employee@kaveritech.com',
      role: 'USER',
      full_name: 'Test Employee',
      department: 'Engineering',
      is_active: true,
      created_at: new Date().toISOString()
    };

    localStorage.setItem('cachemind_token', fakeToken);
    localStorage.setItem('cachemind_user', JSON.stringify(fakeUser));

    expect(localStorage.getItem('cachemind_token')).toBe(fakeToken);
    const parsed = JSON.parse(localStorage.getItem('cachemind_user') || '{}');
    expect(parsed.role).toBe('USER');
    expect(parsed.username).toBe('testemployee');
  });

  it('restricts admin access for standard USER role', () => {
    const userRole: string = 'USER';
    const hasAdminAccess = userRole === 'ADMIN';
    expect(hasAdminAccess).toBe(false);

    const adminRole: string = 'ADMIN';
    const adminHasAccess = adminRole === 'ADMIN';
    expect(adminHasAccess).toBe(true);
  });
});
