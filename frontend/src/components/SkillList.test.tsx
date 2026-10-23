import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { SkillList } from './SkillList'
import { api } from '../api/client'

vi.mock('../api/client', () => ({
  api: {
    listSkills: vi.fn(),
    validateSkills: vi.fn(),
  },
}))

const mockValidationResult = {
  total_files: 3,
  valid: 1,
  missing_frontmatter: 1,
  missing_name: 0,
  missing_description: 0,
  description_too_long: 0,
  invalid_yaml: 0,
  attacker_placeholder: 1,
  skills: [
    {
      path: 'web/offensive-sqli/SKILL.md',
      category: 'web',
      raw_content: '---\nname: offensive-sqli\ndescription: SQL injection skill\n---',
      frontmatter: { name: 'offensive-sqli', description: 'SQL injection skill', category: 'web', tags: [], version: '1.0.0' },
      validation_status: 'valid',
      validation_errors: [],
      has_attacker_com: false,
      attacker_com_locations: [],
    },
    {
      path: 'web/offensive-xss/SKILL.md',
      category: 'web',
      raw_content: '# SKILL: XSS\n\n## Description\nXSS testing',
      frontmatter: { name: 'xss', description: 'XSS testing', category: 'web', tags: [], version: '1.0.0' },
      validation_status: 'missing_frontmatter',
      validation_errors: ['Missing YAML frontmatter', 'Extracted from legacy ## Metadata section (needs frontmatter)'],
      has_attacker_com: false,
      attacker_com_locations: [],
    },
    {
      path: 'web/offensive-rce/SKILL.md',
      category: 'web',
      raw_content: '---\nname: offensive-rce\ndescription: RCE with attacker.com\n---\n\n## Description\nCallback to attacker.com',
      frontmatter: { name: 'offensive-rce', description: 'RCE with attacker.com', category: 'web', tags: [], version: '1.0.0' },
      validation_status: 'attacker_placeholder',
      validation_errors: ['Contains attacker.com placeholder (should use RFC-reserved domains)'],
      has_attacker_com: true,
      attacker_com_locations: [50],
    },
  ],
  validated_at: new Date().toISOString(),
}

describe('SkillList', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders loading state initially', () => {
    render(<SkillList />)
    expect(screen.getByText('Loading skills...')).toBeInTheDocument()
    expect(screen.getByText('Loading skills...')).toBeInTheDocument()
  })

  it('renders skill data when loaded', async () => {
    vi.mocked(api.listSkills).mockResolvedValue(mockValidationResult.skills)
    render(<SkillList />)
    await waitFor(() => {
      expect(screen.getByText('Skill Validation Results')).toBeInTheDocument()
    })
    expect(screen.getByText('Valid: 1')).toBeInTheDocument()
    expect(screen.getByText('Missing Frontmatter: 1')).toBeInTheDocument()
    expect(screen.getByText('Attacker.com: 1')).toBeInTheDocument()
  })

  it('renders skill rows with correct data', async () => {
    vi.mocked(api.listSkills).mockResolvedValue(mockValidationResult.skills)
    render(<SkillList />)
    await waitFor(() => {
      expect(screen.getByText('web/offensive-sqli/SKILL.md')).toBeInTheDocument()
    })
    expect(screen.getByText('web/offensive-xss/SKILL.md')).toBeInTheDocument()
    expect(screen.getByText('web/offensive-rce/SKILL.md')).toBeInTheDocument()
  })

  it('filters by status when select changes', async () => {
    vi.mocked(api.listSkills).mockResolvedValue(mockValidationResult.skills)
    render(<SkillList />)
    await waitFor(() => {
      expect(screen.getByText('Skill Validation Results')).toBeInTheDocument()
    })

    const statusSelect = screen.getByLabelText('Filter by validation status')
    fireEvent.change(statusSelect, { target: { value: 'missing_frontmatter' } })

    await waitFor(() => {
      expect(api.listSkills).toHaveBeenCalledWith(expect.objectContaining({ status: 'missing_frontmatter' }))
    })
  })

  it('shows error state on API failure', async () => {
    vi.mocked(api.listSkills).mockRejectedValue(new Error('Network error'))
    render(<SkillList />)
    await waitFor(() => {
      expect(screen.getByText('Error loading skills')).toBeInTheDocument()
    })
    expect(screen.getByText('Network error')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /retry/i })).toBeInTheDocument()
  })

  it('shows empty state when no skills match filter', async () => {
    vi.mocked(api.listSkills).mockResolvedValue([])
    render(<SkillList />)
    await waitFor(() => {
      expect(screen.getByText('No skills found')).toBeInTheDocument()
    })
  })
})