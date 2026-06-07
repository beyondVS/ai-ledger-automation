import { describe, it, expect, beforeEach, vi } from 'vitest';
import { fetchLedgerList } from '../../src/services/ledgerService';

describe('ledgerService - fetchLedgerList', () => {
  beforeEach(() => {
    vi.stubGlobal('localStorage', {
      getItem: vi.fn().mockReturnValue(JSON.stringify({
        accessToken: 'mocked-jwt-access-token',
        username: 'testuser'
      })),
      setItem: vi.fn(),
      removeItem: vi.fn()
    });
    vi.stubGlobal('fetch', vi.fn());
  });

  it('JWT 토큰을 Authorization 헤더에 동봉하여 GET /api/v1/receipts/ 를 호출한다', async () => {
    const mockData = [
      { id: '1', vendor_name: '테스트상점', total_amount: 10000 }
    ];
    
    fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => mockData
    });

    const result = await fetchLedgerList();

    expect(fetch).toHaveBeenCalledWith('/api/v1/receipts/', {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer mocked-jwt-access-token'
      }
    });
    expect(result).toEqual(mockData);
  });
  
  it('API 응답이 실패하는 경우 에러를 던져야 한다', async () => {
    fetch.mockResolvedValueOnce({
      ok: false,
      status: 401
    });

    await expect(fetchLedgerList()).rejects.toThrow();
  });
});
