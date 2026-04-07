import { useState, useEffect } from 'react';
import { FiSearch, FiDownload, FiMapPin, FiBriefcase, FiAperture } from 'react-icons/fi';

const countryList = [
  "United Kingdom", "France", "Germany", "Netherlands", "Italy", "Spain",
  "Sweden", "Denmark", "Belgium", "Ireland", "Austria", "Switzerland",
  "Portugal", "Norway", "Finland", "Poland", "Czech Republic", "Hungary",
  "Romania", "Greece", "Croatia", "Slovakia", "Slovenia", "Estonia",
  "Latvia", "Lithuania", "Luxembourg", "Malta", "Cyprus", "Bulgaria"
];

const companyTypesList = [
  "Fashion Retailers", "Clothing Brands", "Department Stores",
  "E-commerce Fashion Platforms", "Private Label Brands",
  "Sustainable Fashion Startups", "Luxury Fashion Brands",
  "Streetwear Brands", "Activewear / Sportswear Brands"
];

function App() {
  const [country, setCountry] = useState('United Kingdom');
  const [city, setCity] = useState('');
  const [selectedTypes, setSelectedTypes] = useState(['Clothing Brands', 'Fashion Retailers']);
  const [minScore, setMinScore] = useState(5);
  const [isScraping, setIsScraping] = useState(false);
  const [progress, setProgress] = useState(null);
  const [leads, setLeads] = useState([]);
  const [sessionId, setSessionId] = useState(null);

  const toggleType = (type) => {
    setSelectedTypes(prev => 
      prev.includes(type) ? prev.filter(t => t !== type) : [...prev, type]
    );
  }

  const exportCSV = () => {
    if (!leads.length) return;
    
    // Define headers as requested:
    const headers = ["Company Name", "Person", "Title", "Email", "Website", "About", "Country", "Industry", "Employees", "Revenue", "Founded"];
    
    const rows = leads.map(l => [
      `"${(l.company_name || '').replace(/"/g, '""')}"`,
      `"${(l.key_contact_name || '').replace(/"/g, '""')}"`,
      `"${(l.contact_role || '').replace(/"/g, '""')}"`,
      `"${(l.likely_email || '').replace(/"/g, '""')}"`,
      `"${(l.website || '').replace(/"/g, '""')}"`,
      `"${(l.description || '').replace(/"/g, '""')}"`,
      `"${(l.country || '').replace(/"/g, '""')}"`,
      `"${(l.business_category || '').replace(/"/g, '""')}"`,
      `"${(l.employees_est || '').replace(/"/g, '""')}"`,
      `"${(l.revenue || '').replace(/"/g, '""')}"`,
      `"${(l.founded || '').replace(/"/g, '""')}"`
    ]);

    const csvContent = "data:text/csv;charset=utf-8," 
      + headers.join(",") + "\n" 
      + rows.map(e => e.join(",")).join("\n");
      
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", "bassi_leads_export.csv");
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const startScrape = async () => {
    setIsScraping(true);
    setLeads([]);
    setProgress({ status: 'starting', leads_found: 0, current_action: 'Initializing...' });
    
    try {
      const resp = await fetch('http://localhost:8000/api/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          country,
          city,
          company_types: selectedTypes,
          radius_km: 25,
          min_score: minScore
        })
      });
      const data = await resp.json();
      setSessionId(data.session_id);
    } catch (e) {
      console.error(e);
      setProgress({ status: 'error', current_action: 'Failed to connect to backend', leads_found: 0 });
      setIsScraping(false);
    }
  };

  useEffect(() => {
    let interval;
    if (sessionId && isScraping) {
      interval = setInterval(async () => {
        try {
          const resp = await fetch(`http://localhost:8000/api/progress/${sessionId}`);
          if (resp.ok) {
            const data = await resp.json();
            setProgress(data);
            if (data.status === 'completed' || data.status === 'failed') {
              setIsScraping(false);
              clearInterval(interval);
              // Fetch leads
              const leadsResp = await fetch(`http://localhost:8000/api/results/${sessionId}`);
              if (leadsResp.ok) {
                const leadsData = await leadsResp.json();
                setLeads(leadsData);
              }
            }
          }
        } catch (e) {
          console.error("Polling error", e);
        }
      }, 2000);
    }
    return () => clearInterval(interval);
  }, [sessionId, isScraping]);

  return (
    <div className="min-h-screen bg-neutral-50 text-neutral-900 font-sans">
      <header className="bg-white border-b border-neutral-200 sticky top-0 z-10 shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="bg-indigo-600 text-white p-2 rounded-lg">
              <FiAperture className="w-6 h-6" />
            </div>
            <h1 className="text-2xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-indigo-600 to-purple-600">
              Bassi LeadScraper
            </h1>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
        
        {/* Configurator Section */}
        <div className="bg-white rounded-2xl shadow-sm border border-neutral-200 p-6">
          <h2 className="text-lg font-semibold mb-6 flex items-center gap-2">
            <FiSearch className="text-indigo-500" />
            Search Configuration
          </h2>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-neutral-700 mb-1 flex items-center gap-2"><FiMapPin /> Location</label>
                <div className="flex gap-2">
                  <select value={country} onChange={(e) => setCountry(e.target.value)} className="w-1/2 p-2.5 rounded-lg border border-neutral-300 focus:ring-2 focus:ring-indigo-500 outline-none bg-white">
                    {countryList.map(c => (
                      <option key={c} value={c}>{c}</option>
                    ))}
                  </select>
                  <input type="text" value={city} onChange={(e) => setCity(e.target.value)} placeholder="City (Optional — auto-searches top 3 cities)" className="w-1/2 p-2.5 rounded-lg border border-neutral-300 focus:ring-2 focus:ring-indigo-500 outline-none" />
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-neutral-700 mb-1">Minimum ICP Score (1-10): {minScore}</label>
                <input type="range" min="1" max="10" value={minScore} onChange={(e) => setMinScore(parseInt(e.target.value))} className="w-full accent-indigo-600" />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-neutral-700 mb-2 flex items-center gap-2"><FiBriefcase /> Company Types</label>
              <div className="flex flex-wrap gap-2">
                {companyTypesList.map(type => (
                  <button 
                    key={type} 
                    onClick={() => toggleType(type)}
                    className={`px-3 py-1.5 text-sm rounded-full border transition-all ${selectedTypes.includes(type) ? 'bg-indigo-50 border-indigo-600 text-indigo-700' : 'bg-white border-neutral-300 text-neutral-600 hover:border-indigo-300'}`}
                  >
                    {type}
                  </button>
                ))}
              </div>
            </div>
          </div>

          <div className="mt-8 flex justify-end">
            <button 
              onClick={startScrape} 
              disabled={isScraping}
              className={`px-6 py-2.5 rounded-lg font-medium text-white shadow-sm transition-all focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 flex items-center gap-2 ${isScraping ? 'bg-indigo-400 cursor-not-allowed' : 'bg-indigo-600 hover:bg-indigo-700'}`}
            >
              {isScraping ? (
                <>
                  <svg className="animate-spin h-5 w-5 text-white" fill="none" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg>
                  Scraping...
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
          <div className="bg-white rounded-2xl shadow-sm border border-neutral-200 p-6">
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-lg font-semibold flex items-center gap-2">
                Live Status
              </h2>
              {progress.status === 'completed' && (
                <button onClick={exportCSV} className="text-indigo-600 font-medium text-sm hover:underline flex flex-items gap-1">
                  <FiDownload className="mt-0.5" /> Export CSV
                </button>
              )}
            </div>
            
            <div className="mb-6 p-4 rounded-xl bg-neutral-50 border border-neutral-100 flex items-center gap-4">
              <div className="flex-1">
                <p className="text-sm text-neutral-500 font-medium uppercase tracking-wider mb-1">Current Action</p>
                <p className="text-neutral-800">{progress.current_action}</p>
              </div>
              <div className="text-right">
                <p className="text-sm text-neutral-500 font-medium uppercase tracking-wider mb-1">Leads Found</p>
                <p className="text-3xl font-light text-indigo-600">{progress.leads_found}</p>
              </div>
            </div>

            {leads.length > 0 && (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-sm text-neutral-600">
                  <thead className="bg-neutral-50 text-neutral-700 uppercase">
                    <tr>
                      <th className="px-4 py-3 rounded-tl-lg">Company</th>
                      <th className="px-4 py-3">Category</th>
                      <th className="px-4 py-3">Location</th>
                      <th className="px-4 py-3">Contact</th>
                      <th className="px-4 py-3">Tier / Score</th>
                      <th className="px-4 py-3 rounded-tr-lg">Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {leads.map((lead, idx) => (
                      <tr key={idx} className="border-b border-neutral-100 last:border-0 hover:bg-neutral-50">
                        <td className="px-4 py-3 font-medium text-neutral-900 max-w-xs">
                          {lead.company_name} <br/>
                          <span className="text-xs text-neutral-500 line-clamp-2">{lead.description}</span>
                          <a href={lead.website} className="text-xs text-indigo-500 font-normal hover:underline block mt-0.5" target="_blank" rel="noreferrer">Website</a>
                        </td>
                        <td className="px-4 py-3">
                          <span className="inline-block px-2 py-1 text-xs rounded-full bg-indigo-50 text-indigo-700 border border-indigo-200 whitespace-nowrap">{lead.business_category}</span>
                        </td>
                        <td className="px-4 py-3">{lead.city}, {lead.country}</td>
                        <td className="px-4 py-3">
                          {lead.key_contact_name} ({lead.contact_role})<br/>
                          <span className="text-xs">{lead.likely_email}</span>
                        </td>
                        <td className="px-4 py-3 whitespace-nowrap">
                          {lead.tier} <span className="ml-2 text-neutral-400">({lead.icp_score}/10)</span>
                        </td>
                        <td className="px-4 py-3">
                          <a href={lead.google_maps_url} target="_blank" rel="noreferrer" className="text-indigo-600 hover:text-indigo-800 font-medium">Maps</a>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  );
}

export default App;
