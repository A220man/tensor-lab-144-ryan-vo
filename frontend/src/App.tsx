import { useEffect, useState } from 'react'
import { SkillList } from './components/SkillList'
import { api, SkillValidationResult } from './api/client'
import './App.css'

function App() {
  const [validationData, setValidationData] = useState<SkillValidationResult | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    loadValidation()
  }, [])

  async function loadValidation() {
    setLoading(true)
    setError(null)
    try {
      const result = await api.validateSkills()
      setValidationData(result)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load validation')
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="app-loading">
        <div className="spinner" />
        <p>Loading validation...</p>
      </div>
    )
  }

  if (error) {
    return (
      <div className="app-error" role="alert">
        <h1>Error</h1>
        <p>{error}</p>
        <button onClick={loadValidation}>Retry</button>
      </div>
    )
  }

  return (
    <div className="app">
      <header className="app-header">
        <h1>tensor-lab-144-ryan-vo</h1>
        <p>Offensive Security Skill Validator</p>
      </header>
      <main className="app-main">
        <SkillList initialData={validationData || undefined} />
      </main>
      <footer className="app-footer">
        <p>Ryan Vo | AI & Machine Learning</p>
      </footer>
    </div>
  )
}

export default App