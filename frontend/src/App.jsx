import { useState, useEffect, useMemo } from 'react';
import {
  FiSearch, FiDownload, FiMapPin, FiAperture,
  FiBriefcase, FiFilter, FiGlobe, FiMail, FiUser,
} from 'react-icons/fi';
import './App.css';

const API_BASE = 'http://localhost:8000';

/**
 * Priority badge mapping.
 */
const priorityClass = {
  HIGH: 'high',
  MEDIUM: 'medium',
  LOW: 'low',
};

function App() {
  // ---- State ----
  const [isScraping, setIsScraping] = useState(false);
  const [progress, setProgress] = useState(null);
  const [leads, setLeads] = useState([]);
  const [sessionId, setSessionId] = useState(null);

  // Filters
  const [availableFilters, setAvailableFilters] = useState(null);
  const [selectedBusinessTypes, setSelectedBusinessTypes] = useState([]);
  const [selectedLocations, setSelectedLocations] = useState([]);
  const [exportFormat, setExportFormat] = useState('xlsx');

  // ---- Fetch available filters on mount ----
  useEffect(() => {
    (async () => {
      try {
        const resp = await fetch(`${API_BASE}/api/filters`);
        if (resp.ok) {
          const data = await resp.json();
          setAvailableFilters(data);
        }
      } catch (e) {
        console.error('Failed to fetch filters:', e);
        // Provide fallback filters so the UI still works
        setAvailableFilters({
          business_types: [
            { id: 'block_management', label: 'Block Management Companies', tier: 'Tier 1' },
            { id: 'property_management', label: 'Property Management Companies', tier: 'Tier 1' },
            { id: 'leasehold_management', label: 'Leasehold Management', tier: 'Tier 1' },
            { id: 'rtm_management', label: 'RTM Management Companies', tier: 'Tier 1' },
            { id: 'service_charge', label: 'Service Charge Management', tier: 'Tier 1' },
            { id: 'estate_agent', label: 'Estate Agents', tier: 'Tier 2' },
            { id: 'letting_agent', label: 'Letting Agents', tier: 'Tier 2' },
          ],
          locations: [
            { id: 'all', label: 'All London & Surrounding', group: 'Quick' },
            { id: 'Barnet, London', label: 'Barnet', group: 'North London' },
            { id: 'Enfield, London', label: 'Enfield', group: 'North London' },
            { id: 'Haringey, London', label: 'Haringey', group: 'North London' },
            { id: 'Islington, London', label: 'Islington', group: 'North London' },
            { id: 'Camden, London', label: 'Camden', group: 'North London' },
            { id: 'Finchley, London', label: 'Finchley', group: 'North London' },
            { id: 'Muswell Hill, London', label: 'Muswell Hill', group: 'North London' },
            { id: 'Highgate, London', label: 'Highgate', group: 'North London' },
            { id: 'Crouch End, London', label: 'Crouch End', group: 'North London' },
            { id: 'Tottenham, London', label: 'Tottenham', group: 'North London' },
            { id: 'Wood Green, London', label: 'Wood Green', group: 'North London' },
            { id: 'Archway, London', label: 'Archway', group: 'North London' },
            { id: 'Kentish Town, London', label: 'Kentish Town', group: 'North London' },
            { id: 'Hampstead, London', label: 'Hampstead', group: 'North London' },
            { id: 'Finsbury Park, London', label: 'Finsbury Park', group: 'North London' },
            { id: 'Holloway, London', label: 'Holloway', group: 'North London' },
            { id: 'Angel, London', label: 'Angel', group: 'North London' },
            { id: 'Palmers Green, London', label: 'Palmers Green', group: 'North London' },
            { id: 'Edgware, London', label: 'Edgware', group: 'North London' },
            { id: 'North London', label: 'North London (General)', group: 'Broader London' },
            { id: 'London', label: 'London (City-wide)', group: 'Broader London' },
          ],
        });
      }
    })();
  }, []);

  // ---- Toggle helpers ----
  const toggleBusinessType = (id) => {
    setSelectedBusinessTypes(prev =>
      prev.includes(id) ? prev.filter(x => x !== id) : [...prev, id]
    );
  };

  const toggleLocation = (id) => {
    if (id === 'all') {
      // Toggle "all" — if currently selected, clear. Otherwise select only "all".
      setSelectedLocations(prev =>
        prev.includes('all') ? [] : ['all']
      );
      return;
    }
    // Remove "all" if a specific location is selected
    setSelectedLocations(prev => {
      const without_all = prev.filter(x => x !== 'all');
      return without_all.includes(id)
        ? without_all.filter(x => x !== id)
        : [...without_all, id];
    });
  };

  // ---- Computed query count ----
  const queryCount = useMemo(() => {
    if (!availableFilters) return 0;
    const allBt = selectedBusinessTypes.length === 0;
    const allLoc = selectedLocations.length === 0 || selectedLocations.includes('all');
    // Rough estimate: each business type × each location
    const btCount = allBt
      ? availableFilters.business_types.length
      : selectedBusinessTypes.length;
    const locCount = allLoc
      ? availableFilters.locations.filter(l => l.group !== 'Quick').length
      : selectedLocations.length;
    return Math.min(btCount * locCount, 46); // max 46 queries from master.md
  }, [selectedBusinessTypes, selectedLocations, availableFilters]);

  // ---- Export handler ----
  const downloadFile = async () => {
    if (!sessionId) return;
    try {
      const resp = await fetch(`${API_BASE}/api/export/${sessionId}`);
      if (!resp.ok) {
        console.error('Export not available');
        alert('Download failed: The export file is no longer available. Please run a new scrape.');
        return;
      }
      const blob = await resp.blob();
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `neo_eco_leads_export.${exportFormat}`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
    } catch (e) {
      console.error('Download failed:', e);
    }
  };

  // ---- Start scraping ----
  const startScrape = async () => {
    setIsScraping(true);
    setLeads([]);
    setProgress({ status: 'starting', leads_found: 0, current_action: 'Initialising…' });

    try {
      const resp = await fetch(`${API_BASE}/api/start`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          dry_run: false,
          business_types: selectedBusinessTypes,
          locations: selectedLocations,
          export_format: exportFormat,
        }),
      });
      const data = await resp.json();
      setSessionId(data.session_id);
    } catch (e) {
      console.error(e);
      setProgress({ status: 'error', current_action: 'Failed to connect to backend', leads_found: 0 });
      setIsScraping(false);
    }
  };

  // ---- Poll for progress ----
  useEffect(() => {
    let interval;
    if (sessionId && isScraping) {
      interval = setInterval(async () => {
        try {
          const resp = await fetch(`${API_BASE}/api/progress/${sessionId}`);
          if (resp.ok) {
            const data = await resp.json();
            setProgress(data);
            if (data.status === 'completed' || data.status === 'failed') {
              setIsScraping(false);
              clearInterval(interval);
              const leadsResp = await fetch(`${API_BASE}/api/results/${sessionId}`);
              if (leadsResp.ok) {
                const leadsData = await leadsResp.json();
                setLeads(leadsData);
              }
            }
          }
        } catch (e) {
          console.error('Polling error', e);
        }
      }, 2000);
    }
    return () => clearInterval(interval);
  }, [sessionId, isScraping]);

  // ---- Summary stats ----
  const highCount = leads.filter(l => l.outreach_priority === 'HIGH').length;
  const mediumCount = leads.filter(l => l.outreach_priority === 'MEDIUM').length;
  const lowCount = leads.filter(l => l.outreach_priority === 'LOW').length;
  const emailCount = leads.filter(l => l.email && l.email !== '—' && l.email !== '').length;

  // Group locations by group
  const locationGroups = useMemo(() => {
    if (!availableFilters) return {};
    const groups = {};
    availableFilters.locations.forEach(loc => {
      if (!groups[loc.group]) groups[loc.group] = [];
      groups[loc.group].push(loc);
    });
    return groups;
  }, [availableFilters]);

  // ---- Render ----
  return (
    <div className="app-container">
      {/* Header */}
      <header className="app-header">
        <div className="header-inner">
          <div className="header-brand">
            <div className="header-icon">
              <FiAperture size={22} />
            </div>
            <div>
              <div className="header-title">Neo Eco Cleaning</div>
              <div className="header-subtitle">Lead Generator v2.1</div>
            </div>
          </div>
        </div>
      </header>

      <main className="main-content">

        {/* Filter Configurator */}
        <div className="glass-card">
          <div className="section-header">
            <FiFilter className="section-icon" />
            <span className="section-title">Configure Lead Search</span>
            <span className="section-badge">Google Maps Scraper</span>
          </div>

          <div className="filter-grid">

            {/* Left: Business Type Filters */}
            <div className="filter-panel">
              <div className="filter-panel-header">
                <span className="filter-label">
                  <FiBriefcase style={{ marginRight: 6, verticalAlign: 'middle' }} />
                  Business Type
                </span>
                <div className="filter-actions">
                  <button
                    className="filter-action-btn"
                    onClick={() =>
                      availableFilters &&
                      setSelectedBusinessTypes(availableFilters.business_types.map(b => b.id))
                    }
                  >
                    Select All
                  </button>
                  <button
                    className="filter-action-btn"
                    onClick={() => setSelectedBusinessTypes([])}
                  >
                    Clear
                  </button>
                </div>
              </div>

              <div className="chip-grid">
                {availableFilters?.business_types.map(bt => (
                  <button
                    key={bt.id}
                    className={`chip ${selectedBusinessTypes.includes(bt.id) ? 'active' : ''}`}
                    onClick={() => toggleBusinessType(bt.id)}
                    id={`filter-bt-${bt.id}`}
                  >
                    <span className="chip-dot" />
                    {bt.label}
                    <span className="chip-tier">{bt.tier}</span>
                  </button>
                ))}
              </div>
            </div>

            {/* Right: Location Filters */}
            <div className="filter-panel">
              <div className="filter-panel-header">
                <span className="filter-label">
                  <FiMapPin style={{ marginRight: 6, verticalAlign: 'middle' }} />
                  Locations
                </span>
                <div className="filter-actions">
                  <button
                    className="filter-action-btn"
                    onClick={() => setSelectedLocations(['all'])}
                  >
                    Select All
                  </button>
                  <button
                    className="filter-action-btn"
                    onClick={() => setSelectedLocations([])}
                  >
                    Clear
                  </button>
                </div>
              </div>

              {Object.entries(locationGroups).map(([group, locs]) => (
                <div key={group} className="location-group">
                  <div className="location-group-label">{group}</div>
                  <div className="chip-grid">
                    {locs.map(loc => (
                      <button
                        key={loc.id}
                        className={`chip ${
                          selectedLocations.includes(loc.id) ||
                          (loc.id !== 'all' && selectedLocations.includes('all'))
                            ? 'active'
                            : ''
                        }`}
                        onClick={() => toggleLocation(loc.id)}
                        id={`filter-loc-${loc.id.replace(/[^a-z0-9]/gi, '_')}`}
                      >
                        <span className="chip-dot" />
                        {loc.label}
                      </button>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Export format + Start button row */}
          <div className="export-row">
            <div style={{ display: 'flex', alignItems: 'center', gap: 20 }}>
              <div className="export-format-toggle">
                <button
                  className={`format-btn ${exportFormat === 'xlsx' ? 'active' : ''}`}
                  onClick={() => setExportFormat('xlsx')}
                >
                  .xlsx
                </button>
                <button
                  className={`format-btn ${exportFormat === 'csv' ? 'active' : ''}`}
                  onClick={() => setExportFormat('csv')}
                >
                  .csv
                </button>
              </div>
              <div className="query-summary">
                <FiSearch size={14} />
                <span>
                  <span className="query-count">~{queryCount}</span> queries will run
                </span>
              </div>
            </div>

            <button
              onClick={startScrape}
              disabled={isScraping}
              className="start-btn"
              id="btn-start-scrape"
            >
              {isScraping ? (
                <>
                  <svg className="spinner" width="18" height="18" fill="none" viewBox="0 0 24 24">
                    <circle opacity="0.25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path opacity="0.75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                  </svg>
                  Scraping…
                </>
              ) : (
                <>
                  <FiAperture /> Start Scrape
                </>
              )}
            </button>
          </div>
        </div>

        {/* Progress & Results Section */}
        {progress && (
          <div className="glass-card">
            <div className="section-header">
              {isScraping && <div className="pulse-dot" />}
              <span className="section-title">
                {isScraping ? 'Live Status' : progress.status === 'completed' ? 'Results' : 'Status'}
              </span>
              {progress.status === 'completed' && (
                <button onClick={downloadFile} className="download-btn" id="btn-download">
                  <FiDownload size={14} />
                  Download {exportFormat.toUpperCase()}
                </button>
              )}
            </div>

            {/* Progress bar */}
            <div className="progress-bar-container" style={{ marginBottom: 24 }}>
              <div className="progress-info">
                <div className="progress-label">Current Action</div>
                <div className="progress-action">{progress.current_action}</div>
              </div>
              <div className="progress-count">
                <div className="progress-count-number">{progress.leads_found}</div>
                <div className="progress-count-label">Leads Found</div>
              </div>
            </div>

            {/* Summary badges (visible once completed) */}
            {leads.length > 0 && (
              <>
                <div className="stats-row">
                  <div className="stat-card" style={{ background: 'var(--bg-glass)', border: '1px solid var(--border-subtle)' }}>
                    <div className="stat-label" style={{ color: 'var(--text-secondary)' }}>TOTAL LEADS FOUND</div>
                    <div className="stat-value" style={{ color: 'var(--text-primary)' }}>{leads.length}</div>
                  </div>
                </div>

                <div style={{ marginBottom: 20, display: 'flex', gap: 16, fontSize: '0.8rem' }}>
                  <span style={{ color: 'var(--text-muted)' }}>
                    Total: <strong style={{ color: 'var(--text-primary)' }}>{leads.length}</strong>
                  </span>
                  <span style={{ color: 'var(--text-muted)' }}>
                    <FiMail size={12} style={{ verticalAlign: 'middle', marginRight: 4 }} />
                    With Email: <strong style={{ color: 'var(--accent-emerald-light)' }}>{emailCount}</strong>
                  </span>
                </div>

                {/* Results table */}
                <div className="table-container">
                  <table className="results-table">
                    <thead>
                      <tr>
                        <th>Company Name</th>
                        <th>Email</th>
                        <th>Person</th>
                        <th>Designation</th>
                        <th>Industry</th>
                        <th>Company Phone</th>
                        <th>Website</th>
                        <th>Country</th>
                        <th>Borough</th>
                        <th>Area</th>
                        <th>Rating</th>
                        <th>Reviews</th>
                        <th>Description</th>
                      </tr>
                    </thead>
                    <tbody>
                      {leads.map((lead, idx) => {
                        const pClass = priorityClass[lead.outreach_priority] || 'low';
                        const hasEmail = lead.email && lead.email !== '—' && lead.email !== '';
                        return (
                          <tr key={idx}>
                            <td className="cell-name">{lead.business_name}</td>
                            <td className="cell-email">
                              <span className={`email-indicator ${hasEmail ? 'available' : 'missing'}`} />
                              {hasEmail ? (
                                <a href={`mailto:${lead.email.split(',')[0].trim()}`}>
                                  {lead.email}
                                </a>
                              ) : '—'}
                            </td>
                            <td>
                              {lead.contact_person ? (
                                <span style={{ display: 'flex', alignItems: 'center', gap: 4, whiteSpace: 'nowrap' }}>
                                  <FiUser size={11} style={{ color: 'var(--accent-emerald)' }} />
                                  {lead.contact_person}
                                </span>
                              ) : (
                                <span className="cell-muted">—</span>
                              )}
                            </td>
                            <td className="cell-muted">{lead.primary_designation || '—'}</td>
                            <td style={{ whiteSpace: 'nowrap' }}>{lead.industry || '—'}</td>
                            <td style={{ whiteSpace: 'nowrap' }}>{lead.company_phone || '—'}</td>
                            <td className="cell-website">
                              {lead.website ? (
                                <a href={lead.website} target="_blank" rel="noreferrer">
                                  <FiGlobe size={12} style={{ marginRight: 4, verticalAlign: 'middle' }} />
                                  Visit
                                </a>
                              ) : '—'}
                            </td>
                            <td>{lead.country || '—'}</td>
                            <td>{lead.borough}</td>
                            <td style={{ whiteSpace: 'nowrap' }}>{lead.area_zone}</td>
                            <td>{lead.rating || '—'}</td>
                            <td>{lead.review_count}</td>
                            <td className="cell-truncate">{lead.company_description || '—'}</td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </>
            )}

            {/* Empty state during scraping */}
            {!leads.length && progress.status !== 'completed' && progress.status !== 'failed' && (
              <div className="empty-state">
                <div className="empty-state-icon">
                  <FiSearch />
                </div>
                <div className="empty-state-text">
                  Scraping in progress… leads will appear here as they are found.
                </div>
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  );
}

export default App;
