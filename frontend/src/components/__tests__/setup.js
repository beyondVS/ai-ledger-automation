import { vi } from 'vitest'

// jsdom 환경에서의 URL.createObjectURL 및 URL.revokeObjectURL API 모킹
if (typeof window !== 'undefined') {
  window.URL.createObjectURL = vi.fn(() => 'blob:http://localhost:5173/mock-preview-url')
  window.URL.revokeObjectURL = vi.fn()
}
