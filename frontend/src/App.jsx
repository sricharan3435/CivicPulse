import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { divIcon } from 'leaflet';
import { Circle, MapContainer, Marker, TileLayer, Tooltip, useMap, useMapEvents } from 'react-leaflet';
import { BrowserRouter, Navigate, Route, Routes, useNavigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './AuthContext.jsx';
import { AdminLoginPage, LoginPage, SignupPage } from './AuthPages.jsx';

const CATEGORIES = ['Potholes', 'Garbage', 'Water Leaks', 'Streetlight Failures', 'Other'];
const STATUS = { pending: 'Pending review', in_progress: 'In progress', resolved: 'Resolved' };
const START = [20.5937, 78.9629];

async function api(path, options = {}) {
  const response = await fetch(path, options);
  const body = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(body.detail || `Request failed (${response.status})`);
  return body;
}

function MapEvents({ onPick, picking }) {
  useMapEvents({ click(event) { if (picking) onPick([event.latlng.lat, event.latlng.lng]); } });
  return null;
}

function SelectedLocationPin({ center, onMove }) {
  const markerRef = useRef(null);
  return <Marker ref={markerRef} position={center} draggable icon={issuePinIcon('resolved', true, true)} eventHandlers={{ dragend: () => {
    const point = markerRef.current?.getLatLng();
    if (point) onMove([point.lat, point.lng]);
  } }}><Tooltip>Selected report location · drag to adjust</Tooltip></Marker>;
}

function MapController({ center, locationAccuracy, fitAllKey, issues }) {
  const map = useMap();
  useEffect(() => {
    if (!center) return;
    if (locationAccuracy) {
      const latitudeOffset = locationAccuracy / 111_320;
      const longitudeScale = Math.max(0.15, Math.cos((center[0] * Math.PI) / 180));
      const longitudeOffset = locationAccuracy / (111_320 * longitudeScale);
      map.fitBounds([
        [center[0] - latitudeOffset, center[1] - longitudeOffset],
        [center[0] + latitudeOffset, center[1] + longitudeOffset],
      ], { padding: [40, 40], maxZoom: 18, animate: true, duration: 0.7 });
    } else {
      map.flyTo(center, Math.max(map.getZoom(), 17), { duration: 0.7 });
    }
  }, [center, locationAccuracy, map]);
  useEffect(() => {
    if (fitAllKey && issues.length) {
      const bounds = issues.map((issue) => [issue.latitude, issue.longitude]);
      map.fitBounds(bounds, { padding: [42, 42], maxZoom: 15, animate: true, duration: 0.7 });
    }
  }, [fitAllKey, map]);
  return null;
}

function issuePinIcon(status, selected, isNewLocation = false, isFake = false) {
  const color = isNewLocation ? '#548b59' : isFake ? '#7b8084' : status === 'resolved' ? (selected ? '#367a3d' : '#4b9b52') : selected ? '#ba2925' : '#e34d45';
  return divIcon({
    className: `issue-div-icon${selected ? ' selected' : ''}`,
    iconSize: [34, 42],
    iconAnchor: [17, 40],
    popupAnchor: [0, -36],
    html: `<svg class="issue-pin-svg" viewBox="0 0 34 42" role="img" aria-label="${isNewLocation ? 'New report' : 'Issue'} location"><path d="M17 1C8.16 1 1 8.16 1 17c0 11.2 16 24 16 24s16-12.8 16-24C33 8.16 25.84 1 17 1Z" fill="${color}" stroke="white" stroke-width="2"/><circle cx="17" cy="17" r="6" fill="white"/><circle cx="17" cy="17" r="2.5" fill="${color}"/></svg>`,
  });
}

function IssueMap({ issues, center, locationAccuracy, picking, onPick, selected, onSelect, fitAllKey }) {
  return <MapContainer center={center || START} zoom={center ? 13 : 4} scrollWheelZoom className={`issue-map ${picking ? 'map-picking' : ''}`}>
    <TileLayer attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors' url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
    <MapEvents onPick={onPick} picking={picking} /><MapController center={center} locationAccuracy={locationAccuracy} fitAllKey={fitAllKey} issues={issues} />
    {issues.map((issue) => <IssueMapPin key={issue.id} issue={issue} selected={selected === issue.id} onSelect={onSelect} />)}
    {center && locationAccuracy && <Circle center={center} radius={locationAccuracy} pathOptions={{ color: '#688d50', fillColor: '#a9cc7c', fillOpacity: 0.16, weight: 1 }} />}
    {center && <SelectedLocationPin center={center} onMove={onPick} />}
  </MapContainer>;
}

function IssueMapPin({ issue, selected, onSelect }) {
  const map = useMap();
  return <Marker
    position={[issue.latitude, issue.longitude]}
    icon={issuePinIcon(issue.status, selected, false, issue.is_fake)}
    eventHandlers={{ click: () => { map.flyTo([issue.latitude, issue.longitude], 18, { duration: 0.7 }); onSelect(issue.id); } }}
  ><Tooltip><strong>{issue.title}</strong><br />{issue.is_fake ? 'Marked as fake' : STATUS[issue.status]}</Tooltip></Marker>;
}

function formatDate(value) {
  return new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value));
}

function Stat({ icon, value, label, tone = '' }) {
  return <div className="stat"><span className={`stat-icon ${tone}`}>{icon}</span><div><strong>{value ?? '—'}</strong><span>{label}</span></div></div>;
}

function IssueCard({ issue, isAdmin, onUpdate }) {
  const [team, setTeam] = useState(issue.assigned_team || '');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  useEffect(() => setTeam(issue.assigned_team || ''), [issue.assigned_team]);
  async function save(patch) {
    setSaving(true); setError('');
    try { await onUpdate(issue.id, patch); }
    catch (err) { setError(err.message); }
    finally { setSaving(false); }
  }
  return <article className="issue-card">
    <div className="issue-card-head"><div><div className="card-tags"><span className="category-tag">{issue.category}</span><span className={`status-pill status-${issue.status}`}>{STATUS[issue.status]}</span>{issue.is_fake && <span className="fake-pill">Marked fake</span>}</div><h3>{issue.title}</h3></div></div>
    {issue.image_url && <a className="photo-preview" href={issue.image_url} target="_blank" rel="noreferrer"><img src={issue.image_url} alt={`Community photo for ${issue.title}`} loading="lazy" /><span>View photo ↗</span></a>}
    <p className="issue-description">{issue.description}</p>
    <div className="issue-meta"><span>#{issue.id}</span><span>{formatDate(issue.created_at)}</span>{issue.verified && <span className="verified-label">✓ Verified</span>}{issue.duplicate_of_id && <span className="duplicate-label">Possible duplicate of #{issue.duplicate_of_id}</span>}</div>
    <a className="map-link" href={`https://www.openstreetmap.org/?mlat=${issue.latitude}&mlon=${issue.longitude}#map=17/${issue.latitude}/${issue.longitude}`} target="_blank" rel="noreferrer">◎ View on map</a>
    {isAdmin && <div className="coordinator-tools"><div className="coordinator-row"><label>Status<select value={issue.status} disabled={saving} onChange={(e) => save({ status: e.target.value })}><option value="pending">Pending</option><option value="in_progress">In progress</option><option value="resolved">Resolved</option></select></label><label>Assigned team<input value={team} disabled={saving} placeholder="e.g. Ward 12 roads" maxLength={100} onChange={(e) => setTeam(e.target.value)} /></label></div><div className="coordinator-actions"><button onClick={() => save({ assigned_team: team || null })} disabled={saving}>Save assignment</button><button onClick={() => save({ verified: !issue.verified })} disabled={saving}>{issue.verified ? 'Unverify' : 'Mark verified'}</button><button className={issue.is_fake ? 'restore-fake-action' : 'fake-action'} onClick={() => save({ is_fake: !issue.is_fake })} disabled={saving}>{issue.is_fake ? 'Restore issue' : 'Mark as fake'}</button></div>{error && <div className="inline-error">{error}</div>}</div>}
  </article>;
}

function Dashboard() {
  const { user, signOut } = useAuth();
  const navigate = useNavigate();
  const isAdmin = user.role === 'admin';
  const [issues, setIssues] = useState([]);
  const [stats, setStats] = useState(null);
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState(null);
  const [search, setSearch] = useState('');
  const [category, setCategory] = useState('');
  const [status, setStatus] = useState('');
  const [center, setCenter] = useState(null);
  const [selected, setSelected] = useState(null);
  const [fitAllKey, setFitAllKey] = useState(0);
  const [picking, setPicking] = useState(false);
  const [gpsAccuracy, setGpsAccuracy] = useState(null);
  const [locationBusy, setLocationBusy] = useState(false);
  const [locationLabel, setLocationLabel] = useState('');
  const [placeQuery, setPlaceQuery] = useState('');
  const [placeResults, setPlaceResults] = useState([]);
  const [placeBusy, setPlaceBusy] = useState(false);
  const [placeError, setPlaceError] = useState('');
  const [profileOpen, setProfileOpen] = useState(false);
  const [form, setForm] = useState({ title: '', description: '', category: '', latitude: '', longitude: '' });
  const [photo, setPhoto] = useState(null);
  const [imagePreview, setImagePreview] = useState('');

  const load = useCallback(async () => {
    const params = new URLSearchParams();
    if (category) params.set('category', category);
    if (status) params.set('status', status);
    if (search.trim()) params.set('q', search.trim());
    const [nextIssues, nextStats] = await Promise.all([api(`/api/issues?${params}`), api('/api/issues/stats')]);
    setIssues(nextIssues); setStats(nextStats);
  }, [isAdmin, category, search, status]);

  useEffect(() => { load().catch((error) => setNotice({ type: 'error', text: `Could not load CivicPulse: ${error.message}` })); }, [load]);
  useEffect(() => { if (!photo) { setImagePreview(''); return; } const url = URL.createObjectURL(photo); setImagePreview(url); return () => URL.revokeObjectURL(url); }, [photo]);

  function chooseLocation(coords, accuracy = null, label = 'Map location selected') {
    const next = { ...form, latitude: String(coords[0]), longitude: String(coords[1]) };
    setForm(next); setCenter(coords); setGpsAccuracy(accuracy); setLocationLabel(label); setPicking(false);
  }

  function useMyLocation() {
    if (!navigator.geolocation) { setNotice({ type: 'error', text: 'This browser does not support location access.' }); return; }
    setNotice(null); setLocationBusy(true);
    navigator.geolocation.getCurrentPosition((position) => {
      chooseLocation([position.coords.latitude, position.coords.longitude], position.coords.accuracy, 'Current device location');
      setLocationBusy(false);
    }, (error) => {
      const detail = error.code === 1 ? 'Location permission is blocked. Allow it in your browser settings, or choose the spot on the map.' : error.code === 3 ? 'Getting your location timed out. Try again outdoors or choose the spot on the map.' : 'Your device could not determine a location. Try again or choose the spot on the map.';
      setLocationBusy(false); setNotice({ type: 'error', text: detail });
    }, { enableHighAccuracy: true, timeout: 30000, maximumAge: 0 });
  }

  async function searchPlace() {
    const query = placeQuery.trim();
    if (query.length < 3) { setPlaceError('Enter at least 3 characters to search.'); return; }
    setPlaceBusy(true); setPlaceError(''); setPlaceResults([]);
    try {
      const data = await api(`/api/geocode/search?q=${encodeURIComponent(query)}`);
      setPlaceResults(data.results);
      if (!data.results.length) setPlaceError('No matching places found. Try adding a street, town, or city.');
    } catch (error) { setPlaceError(error.message); }
    finally { setPlaceBusy(false); }
  }

  async function submitIssue(event) {
    event.preventDefault(); setBusy(true); setNotice(null);
    try {
      let image_url;
      if (photo) {
        const body = new FormData(); body.append('photo', photo); body.append('latitude', form.latitude); body.append('longitude', form.longitude);
        const uploaded = await api('/api/issues/upload', { method: 'POST', body }); image_url = uploaded.image_url;
      }
      const created = await api('/api/issues', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ ...form, latitude: Number(form.latitude), longitude: Number(form.longitude), image_url }) });
      setNotice({ type: 'success', text: `Report submitted successfully. Current status: ${STATUS[created.status] || 'Pending review'}.` });
      setForm({ title: '', description: '', category: '', latitude: '', longitude: '' }); setCenter(null); setGpsAccuracy(null); setLocationLabel(''); setSelected(null); setPhoto(null);
      await load();
    } catch (error) { setNotice({ type: 'error', text: error.message }); }
    finally { setBusy(false); }
  }

  async function updateIssue(id, patch) {
    await api(`/api/admin/issues/${id}`, { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(patch) });
    await load();
  }

  const shownIssues = useMemo(() => issues, [issues]);
  return <>
    <header className="topbar"><a className="brand" href="#top"><span className="brand-mark">C</span><span>Civic<span className="brand-light">Pulse</span></span></a><nav><a href="#reports">Explore reports</a><a href="#report" className="nav-cta">Report an issue <span>↗</span></a><div className="profile-wrap"><button className="profile-button" aria-expanded={profileOpen} onClick={() => setProfileOpen(!profileOpen)}><span className="profile-avatar">{user.full_name.trim().charAt(0).toUpperCase()}</span>Profile <span className="profile-chevron">⌄</span></button>{profileOpen && <div className="profile-menu"><span className="profile-menu-label">SIGNED IN AS</span><strong>{user.full_name}</strong><span className="profile-email">{user.email}</span><button onClick={async () => { await signOut(); navigate('/login', { replace: true }); }}>Sign out</button></div>}</div></nav></header>
    <main id="top">
      <section className="hero"><div className="hero-copy"><div className="eyebrow"><span className="pulse-dot" /> CIVIC PULSE · COMMUNITY ACTION</div><h1>Making civic problems visible.<br /><span>Making resolution accountable.</span></h1><p>Report infrastructure issues, see what needs attention around you, and follow each report toward resolution.</p><a className="button button-lime" href="#report">Make a report <span>↓</span></a></div><div className="hero-visual" aria-hidden="true"><div className="hero-sun" /><div className="hero-ring ring-a" /><div className="hero-ring ring-b" /><span className="hero-pin pin-a">●</span><span className="hero-pin pin-b">+</span><div className="hero-hill" /><div className="hero-stamp">LOCAL<br /><b>MATTERS</b></div></div><div className="hero-foot"><span>VISIBLE REPORTS</span><span>ACCOUNTABLE RESOLUTION</span></div></section>
      <section className="stats"><Stat icon="◎" value={stats?.total} label="Community reports" /><Stat icon="◷" value={stats?.pending} label="Awaiting review" tone="amber" /><Stat icon="↗" value={stats?.in_progress} label="Being worked on" tone="blue" /><Stat icon="✓" value={stats?.resolved} label="Resolved" tone="green" /></section>
      <section className="workspace">
        <section className="panel report-form" id="report"><div className="section-kicker">HELP YOUR COMMUNITY</div><h2>Report a civic issue</h2><p className="panel-lede">Share clear details and a location so the right people can act.</p>
          <form onSubmit={submitIssue}>
            <label>Issue title <em>*</em><input value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} minLength="5" maxLength="120" placeholder="e.g. Large pothole on Oak Street" required /></label>
            <label>Issue category <em>*</em><select value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })} required><option value="">Choose a category</option>{CATEGORIES.map((item) => <option key={item}>{item}</option>)}</select></label>
            <label>Description <em>*</em><textarea value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} minLength="10" maxLength="1000" rows="4" placeholder="What happened? Add details that could help the assigned team." required /></label>
            <div className="location-heading"><label>Issue location <em>*</em></label><button type="button" className="text-button" onClick={useMyLocation} disabled={locationBusy}>{locationBusy ? 'Finding precise location…' : '◎ Use my location'}</button></div>
            <div className="place-search">
              <div className="place-search-row"><input value={placeQuery} onChange={(e) => setPlaceQuery(e.target.value)} onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); searchPlace(); } }} placeholder="Search street, road, or landmark" aria-label="Search for a road or place" /><button type="button" className="button button-outline" onClick={searchPlace} disabled={placeBusy}>{placeBusy ? 'Searching…' : 'Search'}</button></div>
              <div className="geocode-disclosure">Place search uses OpenStreetMap. Your query is sent only when you press Search.</div>
              {placeError && <div className="place-error" role="status">{placeError}</div>}
              {!!placeResults.length && <div className="place-results">{placeResults.map((place, index) => <button type="button" key={`${place.latitude}-${place.longitude}-${index}`} onClick={() => { chooseLocation([place.latitude, place.longitude], null, place.name); setPlaceQuery(place.name); setPlaceResults([]); setPlaceError(''); }}><span>⌖</span>{place.name}</button>)}</div>}
            </div>
            <div className={`location-status ${form.latitude ? 'has-location' : ''}`}>{form.latitude ? <>{Number(form.latitude).toFixed(6)}, {Number(form.longitude).toFixed(6)}{locationLabel && <><br /><span className="gps-accuracy">{gpsAccuracy ? `${locationLabel} · estimated accuracy ±${Math.round(gpsAccuracy)} m. Drag the pin to the exact road if needed.` : `${locationLabel} · drag the green pin to fine-tune the exact point.`}</span></>}</> : picking ? 'Click on the map to place the report' : 'Choose a location using GPS, place search, or the map'}</div>
            <div className="form-buttons"><button type="button" className={`button button-outline ${picking ? 'is-picking' : ''}`} onClick={() => setPicking(!picking)}>{picking ? 'Cancel map selection' : '⌖ Pick on map'}</button><label className="button button-outline photo-button">{photo ? 'Change photo' : '＋ Add a photo'}<input type="file" accept="image/jpeg,image/png,image/webp" onChange={(e) => setPhoto(e.target.files?.[0] || null)} /></label></div>
            {imagePreview && <div className="photo-upload-preview"><img src={imagePreview} alt="Selected civic issue" /><div><strong>{photo.name}</strong><span>Watermarked with location and upload time</span><button type="button" className="text-button" onClick={() => setPhoto(null)}>Remove photo</button></div></div>}
            <p className="privacy-note">Reports and map locations are visible to the community. Optional photos are watermarked and stored with Cloudinary.</p>
            <button type="submit" className="button button-dark submit-button" disabled={busy || !form.latitude}>{busy ? 'Submitting report…' : 'Submit community report'}<span>→</span></button>
          </form>
        </section>
        <section className="panel map-panel"><div className="map-heading"><div><div className="section-kicker">SEE THE BIGGER PICTURE</div><h2>Issue map</h2></div><div className="map-tools"><button className="fit-all-button" onClick={() => setFitAllKey((key) => key + 1)} disabled={!issues.length}>⌖ Show all locations</button><div className="map-legend"><span><i className="dot dot-issue" /> Issue locations</span><span><i className="dot dot-selected" /> New report pin</span></div></div></div><IssueMap issues={shownIssues} center={center} locationAccuracy={gpsAccuracy} picking={picking} onPick={chooseLocation} selected={selected} onSelect={setSelected} fitAllKey={fitAllKey} /><div className="map-caption">{picking ? 'Click anywhere on the map to set a report location.' : `${issues.length} reports shown · select a pin to zoom to street level.`}</div>
          <div className="list-heading" id="reports"><div><div className="section-kicker">COMMUNITY ACTIVITY</div><h2>Recent reports</h2></div><button className="refresh-button" aria-label="Refresh reports" onClick={() => load().catch((error) => setNotice({ type: 'error', text: error.message }))}>↻</button></div>
          <div className="filters"><input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="⌕  Search reports" aria-label="Search reports" /><select value={category} onChange={(e) => setCategory(e.target.value)} aria-label="Filter by category"><option value="">All categories</option>{CATEGORIES.map((item) => <option key={item}>{item}</option>)}</select><select value={status} onChange={(e) => setStatus(e.target.value)} aria-label="Filter by status"><option value="">All statuses</option><option value="pending">Pending</option><option value="in_progress">In progress</option><option value="resolved">Resolved</option></select></div>
          <div className="issue-list">{issues.length ? issues.map((issue) => <IssueCard key={issue.id} issue={issue} isAdmin={isAdmin} onUpdate={updateIssue} />) : <div className="empty-state">No reports match these filters. Submit the first report for your community.</div>}</div>
        </section>
      </section>
      {notice && <div className={`notice notice-${notice.type}`} role="status"><span>{notice.text}</span><button onClick={() => setNotice(null)} aria-label="Dismiss">×</button></div>}
    </main>
  </>;
}

function RouteContent() {
  const { user, loading } = useAuth();
  if (loading) return <div className="auth-loading"><span className="loading-spinner" />Loading CivicPulse…</div>;
  return <Routes>
    <Route path="/login" element={user ? <Navigate to="/" replace /> : <LoginPage />} />
    <Route path="/signup" element={user ? <Navigate to="/" replace /> : <SignupPage />} />
    <Route path="/admin-login" element={<AdminLoginPage />} />
    <Route path="/" element={user ? <Dashboard /> : <Navigate to="/login" replace />} />
    <Route path="*" element={<Navigate to={user ? '/' : '/login'} replace />} />
  </Routes>;
}

export default function App() {
  return <AuthProvider><BrowserRouter><RouteContent /></BrowserRouter></AuthProvider>;
}
