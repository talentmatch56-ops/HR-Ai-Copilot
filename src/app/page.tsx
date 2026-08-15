'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { Shield, Sparkles, User, Lock, ArrowRight } from 'lucide-react'

export default function LoginPage() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('password123')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const router = useRouter()

  const handleLogin = async (e: React.FormEvent, presetEmail?: string) => {
    if (e) e.preventDefault()
    setLoading(true)
    setError('')

    const targetEmail = presetEmail || email
    if (!targetEmail) {
      setError('Please enter a valid email address.')
      setLoading(false)
      return
    }

    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
      const res = await fetch(`${apiUrl}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: targetEmail, password })
      })

      if (!res.ok) throw new Error('Authentication failed')

      const data = await res.json()
      localStorage.setItem('hr_token', data.access_token)
      localStorage.setItem('hr_user', JSON.stringify(data.user))
      router.push('/dashboard')
    } catch (err: any) {
      setError(err.message || 'Connection failed. Make sure FastAPI server is running.')
    } finally {
      setLoading(false)
    }
  }

  const demoAccounts = [
    { label: 'Admin (Full Access)', email: 'admin@company.com', icon: '👑' },
    { label: 'HR Director', email: 'hr@company.com', icon: '🎯' },
    { label: 'Engineering Manager', email: 'manager@company.com', icon: '⚙️' },
    { label: 'Software Engineer', email: 'employee@company.com', icon: '💻' },
  ]

  return (
    <div className="min-h-screen flex items-center justify-center relative overflow-hidden"
      style={{ background: 'linear-gradient(135deg, #e0eaff 0%, #f0f7ff 40%, #dff0fb 100%)' }}
    >
      {/* Decorative blobs */}
      <div style={{
        position: 'absolute', top: '-80px', left: '-80px',
        width: '360px', height: '360px',
        background: 'radial-gradient(circle, rgba(99,102,241,0.15) 0%, transparent 70%)',
        borderRadius: '50%', filter: 'blur(40px)', zIndex: 0
      }} />
      <div style={{
        position: 'absolute', bottom: '-80px', right: '-80px',
        width: '400px', height: '400px',
        background: 'radial-gradient(circle, rgba(56,189,248,0.15) 0%, transparent 70%)',
        borderRadius: '50%', filter: 'blur(40px)', zIndex: 0
      }} />
      <div style={{
        position: 'absolute', top: '40%', right: '10%',
        width: '200px', height: '200px',
        background: 'radial-gradient(circle, rgba(139,92,246,0.1) 0%, transparent 70%)',
        borderRadius: '50%', filter: 'blur(30px)', zIndex: 0
      }} />

      {/* Card */}
      <div style={{
        position: 'relative', zIndex: 1,
        width: '100%', maxWidth: '440px',
        background: 'rgba(255,255,255,0.85)',
        backdropFilter: 'blur(20px)',
        WebkitBackdropFilter: 'blur(20px)',
        border: '1px solid rgba(99,102,241,0.15)',
        borderRadius: '24px',
        boxShadow: '0 8px 40px rgba(99,102,241,0.12), 0 2px 8px rgba(0,0,0,0.06)',
        padding: '40px 36px',
        margin: '16px'
      }}>

        {/* Logo + Title */}
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', marginBottom: '28px' }}>
          <div style={{
            width: '56px', height: '56px', borderRadius: '16px',
            background: 'linear-gradient(135deg, #6366f1 0%, #818cf8 100%)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            boxShadow: '0 4px 20px rgba(99,102,241,0.35)',
            marginBottom: '14px'
          }}>
            <Sparkles style={{ width: '26px', height: '26px', color: '#fff' }} />
          </div>
          <h1 style={{ fontSize: '22px', fontWeight: 800, color: '#1e1b4b', letterSpacing: '-0.5px', margin: 0 }}>
            HR AI Copilot
          </h1>
          <p style={{ fontSize: '13px', color: '#6b7280', marginTop: '4px' }}>
            Enterprise Intelligent HR Assistant
          </p>
        </div>

        {/* Error */}
        {error && (
          <div style={{
            marginBottom: '16px', padding: '10px 14px',
            background: '#fef2f2', border: '1px solid #fecaca',
            color: '#dc2626', fontSize: '12px', borderRadius: '10px', textAlign: 'center'
          }}>
            {error}
          </div>
        )}

        {/* Form */}
        <form onSubmit={(e) => handleLogin(e)} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          {/* Email */}
          <div>
            <label style={{ display: 'block', fontSize: '11px', fontWeight: 700, color: '#4b5563', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: '6px' }}>
              Email Address
            </label>
            <div style={{ position: 'relative' }}>
              <span style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)', color: '#9ca3af', display: 'flex' }}>
                <User style={{ width: '16px', height: '16px' }} />
              </span>
              <input
                type="email"
                required
                placeholder="you@company.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                style={{
                  width: '100%', boxSizing: 'border-box',
                  background: '#f8fafc', border: '1.5px solid #e2e8f0',
                  borderRadius: '10px', padding: '10px 14px 10px 38px',
                  fontSize: '13px', color: '#1e293b',
                  outline: 'none', transition: 'border-color 0.2s'
                }}
                onFocus={e => e.target.style.borderColor = '#6366f1'}
                onBlur={e => e.target.style.borderColor = '#e2e8f0'}
              />
            </div>
          </div>

          {/* Password */}
          <div>
            <label style={{ display: 'block', fontSize: '11px', fontWeight: 700, color: '#4b5563', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: '6px' }}>
              Password
            </label>
            <div style={{ position: 'relative' }}>
              <span style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)', color: '#9ca3af', display: 'flex' }}>
                <Lock style={{ width: '16px', height: '16px' }} />
              </span>
              <input
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                style={{
                  width: '100%', boxSizing: 'border-box',
                  background: '#f8fafc', border: '1.5px solid #e2e8f0',
                  borderRadius: '10px', padding: '10px 14px 10px 38px',
                  fontSize: '13px', color: '#1e293b',
                  outline: 'none', transition: 'border-color 0.2s'
                }}
                onFocus={e => e.target.style.borderColor = '#6366f1'}
                onBlur={e => e.target.style.borderColor = '#e2e8f0'}
              />
            </div>
          </div>

          {/* Sign In button */}
          <button
            type="submit"
            disabled={loading}
            style={{
              width: '100%', padding: '11px',
              background: loading ? '#a5b4fc' : 'linear-gradient(135deg, #6366f1 0%, #818cf8 100%)',
              color: '#fff', fontWeight: 700, fontSize: '14px',
              border: 'none', borderRadius: '10px', cursor: loading ? 'not-allowed' : 'pointer',
              display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px',
              boxShadow: '0 4px 16px rgba(99,102,241,0.3)',
              transition: 'all 0.2s'
            }}
          >
            {loading ? 'Signing in...' : 'Sign In'}
            {!loading && <ArrowRight style={{ width: '16px', height: '16px' }} />}
          </button>
        </form>

        {/* Divider */}
        <div style={{ position: 'relative', margin: '22px 0', display: 'flex', alignItems: 'center' }}>
          <div style={{ flex: 1, height: '1px', background: '#e2e8f0' }} />
          <span style={{ padding: '0 12px', fontSize: '10px', fontWeight: 700, color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.08em', background: 'transparent' }}>
            Or Quick Access Demo
          </span>
          <div style={{ flex: 1, height: '1px', background: '#e2e8f0' }} />
        </div>

        {/* Demo accounts */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
          {demoAccounts.map((account) => (
            <button
              key={account.email}
              onClick={(e) => handleLogin(e, account.email)}
              style={{
                display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
                padding: '10px 8px', borderRadius: '10px',
                border: '1.5px solid #e2e8f0',
                background: '#f8fafc',
                cursor: 'pointer', transition: 'all 0.18s',
                gap: '4px'
              }}
              onMouseEnter={e => {
                (e.currentTarget as HTMLButtonElement).style.borderColor = '#6366f1'
                ;(e.currentTarget as HTMLButtonElement).style.background = '#eef2ff'
              }}
              onMouseLeave={e => {
                (e.currentTarget as HTMLButtonElement).style.borderColor = '#e2e8f0'
                ;(e.currentTarget as HTMLButtonElement).style.background = '#f8fafc'
              }}
            >
              <span style={{ fontSize: '18px' }}>{account.icon}</span>
              <span style={{ fontSize: '11px', fontWeight: 600, color: '#374151', textAlign: 'center', lineHeight: '1.3' }}>{account.label}</span>
              <span style={{ fontSize: '9px', color: '#9ca3af' }}>{account.email}</span>
            </button>
          ))}
        </div>

        {/* Footer */}
        <p style={{ fontSize: '10px', textAlign: 'center', color: '#9ca3af', marginTop: '20px', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '4px' }}>
          <Shield style={{ width: '12px', height: '12px', color: '#6366f1' }} />
          Secure Sandbox Environment
        </p>
      </div>
    </div>
  )
}
