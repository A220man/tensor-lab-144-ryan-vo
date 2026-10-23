import '@testing-library/jest-dom'
import { vi } from 'vitest'

// Mock react-router-dom before any imports
vi.mock('react-router-dom', () => ({
  useNavigate: () => vi.fn(),
  useParams: () => ({}),
  Link: ({ children }: { children: unknown }) => children,
  Outlet: () => null,
}))