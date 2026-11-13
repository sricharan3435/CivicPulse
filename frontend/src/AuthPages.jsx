import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from './AuthContext.jsx';

function AuthShell({ mode, children }) {
  const signup = mode === 'signup';
  const admin = mode === 'admin';
  const title = signup ? 'Create your account' : admin ? 'Administrator access' : 'Sign in to CivicPulse';
  return <div className="auth-layout">
    <aside className="auth-story">
      <Link className="brand auth-brand" to="/"><span className="brand-mark">C</span><span>Civic<span className="brand-light">Pulse</span></span></Link>
      <div className="auth-story-copy"><span className="eyebrow"><i className="pulse-dot" /> COMMUNITY POWERED</span><h1>Every voice can<br /><span>move a city forward.</span></h1><p>Make local problems visible. Help your community follow them through to resolution.</p></div>
      <div className="auth-story-foot">{mode === 'login' ? <Link to="/admin-login" className="admin-login-link">Administrator login <span>→</span></Link> : mode === 'admin' ? <Link to="/login" className="admin-login-link">← Citizen sign in</Link> : <span>MAKING CIVIC PROBLEMS VISIBLE</span>}</div>
    </aside>
    <main className="auth-main"><div className="auth-card"><div className="auth-mobile-brand"><Link className="brand" to="/"><span className="brand-mark">C</span><span>Civic<span className="brand-light">Pulse</span></span></Link></div><div className="auth-kicker">{signup ? 'JOIN YOUR COMMUNITY' : admin ? 'COORDINATOR ACCESS' : 'WELCOME BACK'}</div><h2>{title}</h2><p>{signup ? 'Start reporting and tracking the issues that matter to your neighborhood.' : admin ? 'Sign in with your administrator account to manage reports.' : 'Pick up where your community work left off.'}</p>{children}<div className="auth-switch">{signup ? <>Already have an account? <Link to="/login">Sign in</Link></> : admin ? <>Return to <Link to="/login">citizen sign in</Link></> : <>New to CivicPulse? <Link to="/signup">Create an account</Link></>}</div>{mode === 'login' && <div className="auth-admin-mobile"><Link to="/admin-login">Administrator login</Link></div>}<div className="auth-privacy">Your account helps you manage reports. Your email is not shown on public issue cards.</div></div></main>
  </div>;
}

export function LoginPage() {
  const { signIn } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  async function submit(event) {
    event.preventDefault(); setBusy(true); setError('');
    try { await signIn(email, password); navigate('/', { replace: true }); }
    catch (err) { setError(err.message); }
    finally { setBusy(false); }
  }
  return <AuthShell mode="login"><form className="auth-form" onSubmit={submit}><label>Email address<input type="email" autoComplete="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="you@example.com" required /></label><label>Password<input type="password" autoComplete="current-password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="Your password" required /></label>{error && <div className="auth-error" role="alert">{error}</div>}<button className="button button-dark auth-submit" disabled={busy}>{busy ? 'Signing in…' : 'Sign in'}<span>→</span></button></form></AuthShell>;
}

export function SignupPage() {
  const { signUp } = useAuth();
  const navigate = useNavigate();
  const [values, setValues] = useState({ full_name: '', email: '', password: '', confirm: '' });
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  async function submit(event) {
    event.preventDefault(); setError('');
    if (values.password !== values.confirm) { setError('Your passwords do not match.'); return; }
    setBusy(true);
    try { await signUp(values.full_name, values.email, values.password); navigate('/', { replace: true }); }
    catch (err) { setError(err.message); }
    finally { setBusy(false); }
  }
  return <AuthShell mode="signup"><form className="auth-form" onSubmit={submit}><label>Your name<input autoComplete="name" value={values.full_name} onChange={(e) => setValues({ ...values, full_name: e.target.value })} placeholder="How should we call you?" minLength="2" maxLength="100" required /></label><label>Email address<input type="email" autoComplete="email" value={values.email} onChange={(e) => setValues({ ...values, email: e.target.value })} placeholder="you@example.com" required /></label><label>Password<input type="password" autoComplete="new-password" value={values.password} onChange={(e) => setValues({ ...values, password: e.target.value })} placeholder="At least 10 characters" minLength="10" maxLength="128" required /></label><label>Confirm password<input type="password" autoComplete="new-password" value={values.confirm} onChange={(e) => setValues({ ...values, confirm: e.target.value })} placeholder="Enter your password again" minLength="10" maxLength="128" required /></label>{error && <div className="auth-error" role="alert">{error}</div>}<button className="button button-dark auth-submit" disabled={busy}>{busy ? 'Creating account…' : 'Create account'}<span>→</span></button></form></AuthShell>;
}

export function AdminLoginPage() {
  const { signInAsAdmin } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  async function submit(event) {
    event.preventDefault(); setBusy(true); setError('');
    try {
      await signInAsAdmin(email, password);
      navigate('/', { replace: true });
    } catch (err) { setError(err.message); }
    finally { setBusy(false); }
  }
  return <AuthShell mode="admin"><form className="auth-form" onSubmit={submit}><label>Administrator email<input type="email" autoComplete="username" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="admin@example.com" required /></label><label>Password<input type="password" autoComplete="current-password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="Your administrator password" required /></label>{error && <div className="auth-error" role="alert">{error}</div>}<button className="button button-dark auth-submit" disabled={busy}>{busy ? 'Signing in…' : 'Sign in as administrator'}<span>→</span></button></form></AuthShell>;
}
