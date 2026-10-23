import { useState, useEffect } from 'react'
import { api, SkillValidationResult, SkillValidationStatus } from '../api/client'

interface SkillListProps {
  initialData?: SkillValidationResult
}

export function SkillList({ initialData }: SkillListProps) {
  const [data, setData] = useState<SkillValidationResult | null>(initialData || null)
  const [loading, setLoading] = useState(!initialData)
  const [error, setError] = useState<string | null>(null)
  const [filterStatus, setFilterStatus] = useState<SkillValidationStatus | 'all'>('all')
  const [filterCategory, setFilterCategory] = useState<string>('')
  const [showAttackerOnly, setShowAttackerOnly] = useState(false)

  useEffect(() => {
    if (!initialData) {
      loadData()
    }
  }, [initialData, filterStatus, filterCategory, showAttackerOnly])

  async function loadData() {
    setLoading(true)
    setError(null)
    try {
      const result = await api.listSkills({
        status: filterStatus === 'all' ? undefined : filterStatus,
        category: filterCategory || undefined,
        has_attacker_com: showAttackerOnly ? true : undefined,
      })
      setData({
        total_files: result.length,
        valid: result.filter(s => s.validation_status === 'valid').length,
        missing_frontmatter: result.filter(s => s.validation_status === 'missing_frontmatter').length,
        missing_name: result.filter(s => s.validation_status === 'missing_name').length,
        missing_description: result.filter(s => s.validation_status === 'missing_description').length,
        description_too_long: result.filter(s => s.validation_status === 'description_too_long').length,
        invalid_yaml: result.filter(s => s.validation_status === 'invalid_yaml').length,
        attacker_placeholder: result.filter(s => s.validation_status === 'attacker_placeholder').length,
        skills: result,
        validated_at: new Date().toISOString(),
      })
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load skills')
    } finally {
      setLoading(false)
    }
  }

  const statusColors: Record<SkillValidationStatus, string> = {
    valid: '#22c55e',
    missing_frontmatter: '#ef4444',
    missing_name: '#f97316',
    missing_description: '#f97316',
    description_too_long: '#f59e0b',
    invalid_yaml: '#ef4444',
    attacker_placeholder: '#f59e0b',
  }

  const statusLabels: Record<SkillValidationStatus, string> = {
    valid: 'Valid',
    missing_frontmatter: 'Missing Frontmatter',
    missing_name: 'Missing Name',
    missing_description: 'Missing Description',
    description_too_long: 'Desc > 1024 chars',
    invalid_yaml: 'Invalid YAML',
    attacker_placeholder: 'Has attacker.com',
  }

  if (loading && !data) {
    return (
      <div className="skill-list-loading">
        <div className="spinner" />
        <p>Loading skills...</p>
      </div>
    )
  }

  if (error) {
    return (
      <div className="skill-list-error" role="alert">
        <h3>Error loading skills</h3>
        <p>{error}</p>
        <button onClick={loadData}>Retry</button>
      </div>
    )
  }

  if (!data || data.skills.length === 0) {
    return (
      <div className="skill-list-empty">
        <h3>No skills found</h3>
        <p>{filterStatus !== 'all' || filterCategory || showAttackerOnly ? 'Try adjusting filters' : 'No SKILL.md files in Skills directory'}</p>
      </div>
    )
  }

  const categories = [...new Set(data.skills.map(s => s.category))].sort()

  return (
    <div className="skill-list">
      <div className="skill-list-header">
        <h2>Skill Validation Results</h2>
        <div className="skill-summary">
          <span className={`badge ${data.valid > 0 ? 'valid' : ''}`}>Valid: {data.valid}</span>
          <span className={`badge ${data.missing_frontmatter > 0 ? 'error' : ''}`}>Missing Frontmatter: {data.missing_frontmatter}</span>
          <span className={`badge ${data.attacker_placeholder > 0 ? 'warning' : ''}`}>Attacker.com: {data.attacker_placeholder}</span>
          <span className={`badge ${data.description_too_long > 0 ? 'warning' : ''}`}>Desc &gt; 1024: {data.description_too_long}</span>
        </div>
      </div>

      <div className="skill-filters">
        <select
          value={filterStatus}
          onChange={e => setFilterStatus(e.target.value as SkillValidationStatus | 'all')}
          aria-label="Filter by validation status"
        >
          <option value="all">All Statuses</option>
          <option value="valid">Valid</option>
          <option value="missing_frontmatter">Missing Frontmatter</option>
          <option value="missing_name">Missing Name</option>
          <option value="missing_description">Missing Description</option>
          <option value="description_too_long">Description Too Long</option>
          <option value="invalid_yaml">Invalid YAML</option>
          <option value="attacker_placeholder">Has attacker.com</option>
        </select>

        <select
          value={filterCategory}
          onChange={e => setFilterCategory(e.target.value)}
          aria-label="Filter by category"
        >
          <option value="">All Categories</option>
          {categories.map(cat => (
            <option key={cat} value={cat}>{cat}</option>
          ))}
        </select>

        <label className="checkbox-label">
          <input
            type="checkbox"
            checked={showAttackerOnly}
            onChange={e => setShowAttackerOnly(e.target.checked)}
          />
          Show only attacker.com
        </label>

        <button onClick={loadData} disabled={loading}>
          {loading ? 'Refreshing...' : 'Refresh'}
        </button>
      </div>

      <div className="skill-table-container" role="region" aria-label="Skills table" tabIndex={0}>
        <table className="skill-table">
          <thead>
            <tr>
              <th scope="col">Skill</th>
              <th scope="col">Category</th>
              <th scope="col">Status</th>
              <th scope="col">Name</th>
              <th scope="col">Description</th>
              <th scope="col">Issues</th>
            </tr>
          </thead>
          <tbody>
            {data.skills.map(skill => (
              <tr key={skill.path}>
                <td className="skill-path">{skill.path}</td>
                <td>{skill.category}</td>
                <td>
                  <span
                    className="status-badge"
                    style={{ backgroundColor: statusColors[skill.validation_status as SkillValidationStatus] || '#6b7280' }}
                  >
                    {statusLabels[skill.validation_status as SkillValidationStatus] || skill.validation_status}
                  </span>
                </td>
                <td>{skill.frontmatter?.name || '\u2014'}</td>
                <td className="skill-description">
                  {skill.frontmatter?.description ? (
                    skill.frontmatter.description.length > 80
                      ? skill.frontmatter.description.slice(0, 80) + '\u2026'
                      : skill.frontmatter.description
                  ) : (
                    <em>No description</em>
                  )}
                </td>
                <td>
                  <ul className="error-list">
                    {skill.validation_errors.map((err, i) => (
                      <li key={i}>{err}</li>
                    ))}
                    {skill.has_attacker_com && (
                      <li>Contains attacker.com at {skill.attacker_com_locations.length} location(s)</li>
                    )}
                  </ul>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}