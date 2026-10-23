export interface SkillMetadata {
  name: string
  description: string
  category?: string
  tags?: string[]
  version?: string
  author?: string
}

export interface SkillFile {
  path: string
  category: string
  raw_content: string
  frontmatter?: SkillMetadata
  validation_status: string
  validation_errors: string[]
  has_attacker_com: boolean
  attacker_com_locations: number[]
}

export interface SkillValidationResult {
  total_files: number
  valid: number
  missing_frontmatter: number
  missing_name: number
  missing_description: number
  description_too_long: number
  invalid_yaml: number
  attacker_placeholder: number
  skills: SkillFile[]
  validated_at: string
}

export interface SkillFixResult {
  file_path: string
  success: boolean
  original_frontmatter?: string
  new_frontmatter?: string
  error?: string
}

export type SkillValidationStatus =
  | 'valid'
  | 'missing_frontmatter'
  | 'missing_name'
  | 'missing_description'
  | 'description_too_long'
  | 'invalid_yaml'
  | 'attacker_placeholder'

const API_BASE = '/api'

async function fetchJson<T>(url: string, options?: RequestInit): Promise<T> {
  const response = await fetch(url, {
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
    ...options,
  })

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Unknown error' }))
    throw new Error(error.detail || `HTTP ${response.status}`)
  }

  return response.json()
}

export const api = {
  validateSkills: () => fetchJson<SkillValidationResult>(`${API_BASE}/skills/validate`),

  listSkills: (params?: {
    status?: SkillValidationStatus
    category?: string
    has_attacker_com?: boolean
  }) => {
    const searchParams = new URLSearchParams()
    if (params?.status) searchParams.set('status', params.status)
    if (params?.category) searchParams.set('category', params.category)
    if (params?.has_attacker_com !== undefined) searchParams.set('has_attacker_com', String(params.has_attacker_com))
    return fetchJson<SkillFile[]>(`${API_BASE}/skills/list?${searchParams.toString()}`)
  },

  fixSkill: (skillPath: string) => fetchJson<SkillFixResult>(`${API_BASE}/skills/fix/${encodeURIComponent(skillPath)}`, {
    method: 'POST',
  }),

  fixAllSkills: (apply: boolean = false) =>
    fetchJson<SkillFixResult[]>(`${API_BASE}/skills/fix-all?apply=${apply}`, {
      method: 'POST',
    }),
}