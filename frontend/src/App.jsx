import React, { useState, useEffect } from 'react';
import {
  Search,
  Sparkles,
  ShieldCheck,
  Clock,
  Database,
  CheckCircle2,
  AlertTriangle,
  HelpCircle,
  BarChart3,
  LineChart as LineChartIcon,
  Table as TableIcon,
  Copy,
  Check,
  Settings2,
  X,
  ExternalLink,
  ChevronRight,
  TrendingUp,
  Info
} from 'lucide-react';
import {
  ResponsiveContainer,
  LineChart,
  Line,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend
} from 'recharts';

const PALETTE = ['#2563eb', '#10b981', '#f59e0b', '#ec4899', '#8b5cf6', '#06b6d4', '#f97316', '#64748b'];

export default function App() {
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [seedQuestions, setSeedQuestions] = useState([]);
  const [activeCategory, setActiveCategory] = useState('all');
  const [healthInfo, setHealthInfo] = useState(null);
  const [copiedSQL, setCopiedSQL] = useState(false);
  const [showDataTable, setShowDataTable] = useState(false);
  
  // Settings modal
  const [showSettings, setShowSettings] = useState(false);
  const [apiKey, setApiKey] = useState(() => localStorage.getItem('openrouter_key') || '');
  const [model, setModel] = useState(() => localStorage.getItem('openrouter_model') || 'meta-llama/llama-3.3-70b-instruct:free');

  useEffect(() => {
    fetch('/api/health')
      .then(res => res.json())
      .then(data => setHealthInfo(data))
      .catch(() => {});

    fetch('/api/seed-questions')
      .then(res => res.json())
      .then(data => {
        if (data.questions) setSeedQuestions(data.questions);
      })
      .catch(() => {});
  }, []);

  const handleSaveSettings = (e) => {
    e.preventDefault();
    localStorage.setItem('openrouter_key', apiKey.trim());
    localStorage.setItem('openrouter_model', model.trim());
    setShowSettings(false);
  };

  const handleRunQuery = async (questionText) => {
    const q = (questionText || query).trim();
    if (!q) return;
    setQuery(q);
    setLoading(true);
    setError(null);
    setShowDataTable(false);

    try {
      const res = await fetch('/api/query', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          question: q,
          api_key: apiKey.trim() || undefined,
          model: model.trim() || undefined
        })
      });
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || 'Query execution failed');
      }
      setResult(data);
    } catch (err) {
      setError(err.message);
      setResult(null);
    } finally {
      setLoading(false);
    }
  };

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text);
    setCopiedSQL(true);
    setTimeout(() => setCopiedSQL(false), 2000);
  };

  const categories = [
    { id: 'all', label: 'All Questions' },
    { id: 'cross_dataset', label: 'Youth Unemployment' },
    { id: 'forecast', label: 'Statistical Projections' },
    { id: 'reflection', label: 'Self-Healing (Reflection)' },
    { id: 'lookup', label: 'Lookups' },
    { id: 'comparison', label: 'Comparisons' },
    { id: 'ranking', label: 'Rankings' },
    { id: 'trend', label: 'Trends' },
    { id: 'ambiguous', label: 'Ambiguous' },
    { id: 'unanswerable', label: 'Refusals' },
  ];

  const filteredQuestions = seedQuestions.filter(q => {
    if (activeCategory === 'all') return true;
    return q.category === activeCategory;
  });

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 flex flex-col font-sans">
      {/* Top Navbar */}
      <header className="border-b border-slate-200 bg-white sticky top-0 z-30 shadow-xs">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-blue-700 to-indigo-600 flex items-center justify-center text-white font-bold shadow-md shadow-blue-500/20">
              <TrendingUp className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <h1 className="font-bold text-lg text-slate-900 tracking-tight">Aus Gov Data Explorer</h1>
                <span className="text-xs bg-emerald-100 text-emerald-800 font-semibold px-2 py-0.5 rounded-full border border-emerald-200">
                  ABS 6202.0
                </span>
              </div>
              <p className="text-xs text-slate-500 hidden sm:block">
                Grounded Natural Language Analytics on Australian Labour Force Statistics
              </p>
            </div>
          </div>

          <div className="flex items-center space-x-3">
            <div className="hidden md:flex items-center text-xs text-slate-600 bg-slate-100 px-3 py-1.5 rounded-lg border border-slate-200">
              <Database className="w-3.5 h-3.5 mr-1.5 text-blue-600" />
              <span>433k Monthly Records (1978 – 2026)</span>
            </div>

            <button
              onClick={() => setShowSettings(true)}
              className="flex items-center space-x-1.5 text-xs font-medium text-slate-700 bg-white hover:bg-slate-100 border border-slate-300 px-3 py-1.5 rounded-lg transition-colors cursor-pointer"
            >
              <Settings2 className="w-4 h-4 text-slate-500" />
              <span>{apiKey ? 'OpenRouter Active' : 'Model Settings'}</span>
              {apiKey && <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>}
            </button>
          </div>
        </div>
      </header>

      {/* Main Container */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
        
        {/* Search / NL Input Hero */}
        <section className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6 sm:p-8 relative overflow-hidden">
          <div className="max-w-3xl">
            <h2 className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight mb-2">
              Ask anything about Australian Labour Force & Unemployment
            </h2>
            <p className="text-sm text-slate-600 mb-6">
              Ask in plain English. The system translates your prompt into verified SQL, validates against safety guardrails, generates deterministic charts, and provides fact-grounded summaries.
            </p>

            <form
              onSubmit={(e) => {
                e.preventDefault();
                handleRunQuery();
              }}
              className="flex flex-col sm:flex-row gap-2.5"
            >
              <div className="relative flex-1">
                <Search className="w-5 h-5 absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" />
                <input
                  type="text"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder="e.g. Compare unemployment rate trends between NSW and Victoria"
                  className="w-full pl-11 pr-4 py-3.5 bg-slate-50 border border-slate-300 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-blue-600 focus:bg-white transition-all shadow-inner"
                />
              </div>
              <button
                type="submit"
                disabled={loading || !query.trim()}
                className="bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white font-semibold text-sm px-6 py-3.5 rounded-xl transition-all flex items-center justify-center space-x-2 shadow-sm shadow-blue-600/30 cursor-pointer"
              >
                {loading ? (
                  <>
                    <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                    <span>Analyzing...</span>
                  </>
                ) : (
                  <>
                    <Sparkles className="w-4 h-4" />
                    <span>Explore Data</span>
                  </>
                )}
              </button>
            </form>
          </div>

          {/* Seed Question Pills */}
          <div className="mt-8 pt-6 border-t border-slate-100">
            <div className="flex items-center justify-between flex-wrap gap-2 mb-3">
              <span className="text-xs font-bold uppercase tracking-wider text-slate-500">
                Explore Seed Questions (15+ Pre-configured Scenarios):
              </span>
              
              {/* Category Filter Tabs */}
              <div className="flex flex-wrap gap-1">
                {categories.map(cat => (
                  <button
                    key={cat.id}
                    onClick={() => setActiveCategory(cat.id)}
                    className={`text-xs px-2.5 py-1 rounded-md font-medium transition-colors cursor-pointer ${
                      activeCategory === cat.id
                        ? 'bg-blue-100 text-blue-800 font-semibold'
                        : 'text-slate-500 hover:bg-slate-100'
                    }`}
                  >
                    {cat.label}
                  </button>
                ))}
              </div>
            </div>

            <div className="flex flex-wrap gap-2">
              {filteredQuestions.map(item => (
                <button
                  key={item.id}
                  onClick={() => handleRunQuery(item.question)}
                  className="group inline-flex items-center space-x-2 text-xs bg-slate-100 hover:bg-blue-50 hover:text-blue-700 border border-slate-200 hover:border-blue-300 px-3 py-1.5 rounded-lg text-slate-700 transition-all text-left cursor-pointer"
                >
                  <span className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${
                    item.category === 'cross_dataset' ? 'bg-indigo-100 text-indigo-800' :
                    item.category === 'forecast' ? 'bg-purple-100 text-purple-800' :
                    item.category === 'reflection' ? 'bg-emerald-100 text-emerald-800' :
                    item.category === 'ambiguous' || item.category === 'ambiguous_forecast' ? 'bg-amber-100 text-amber-800' :
                    item.category === 'unanswerable' || item.category === 'reflection_failure' ? 'bg-rose-100 text-rose-800' :
                    item.category === 'out_of_scope' ? 'bg-slate-200 text-slate-800' :
                    'bg-slate-200 text-slate-700'
                  }`}>
                    {item.badge}
                  </span>
                  <span>{item.question}</span>
                  <ChevronRight className="w-3 h-3 text-slate-400 group-hover:text-blue-600 transition-transform group-hover:translate-x-0.5" />
                </button>
              ))}
            </div>
          </div>
        </section>

        {/* Query Result Section */}
        {error && (
          <div className="bg-rose-50 border border-rose-200 rounded-2xl p-6 text-rose-800 flex items-start space-x-3">
            <AlertTriangle className="w-5 h-5 text-rose-600 shrink-0 mt-0.5" />
            <div>
              <h3 className="font-bold text-sm">Query Failed</h3>
              <p className="text-xs text-rose-700 mt-1">{error}</p>
            </div>
          </div>
        )}

        {result && result.status === 'refusal' && (
          <div className="bg-amber-50 border border-amber-200 rounded-2xl p-6 text-amber-900 shadow-sm animate-in fade-in duration-300">
            <div className="flex items-start space-x-3.5">
              <div className="p-2 bg-amber-100 rounded-xl text-amber-700 shrink-0">
                <HelpCircle className="w-6 h-6" />
              </div>
              <div className="flex-1">
                <div className="flex items-center space-x-2">
                  <span className="text-xs font-bold uppercase tracking-wider bg-amber-200/80 text-amber-900 px-2 py-0.5 rounded">
                    Guardrail Activated: {result.intent_type.replace('_', ' ').toUpperCase()}
                  </span>
                </div>
                <p className="text-sm font-medium text-amber-950 mt-2 leading-relaxed whitespace-pre-line">
                  {result.message}
                </p>

                {result.suggested_queries && result.suggested_queries.length > 0 && (
                  <div className="mt-4 pt-4 border-t border-amber-200/60">
                    <span className="text-xs font-semibold text-amber-800 uppercase tracking-wider block mb-2">
                      Suggested Valid Queries:
                    </span>
                    <div className="flex flex-col sm:flex-row flex-wrap gap-2">
                      {result.suggested_queries.map((sq, i) => (
                        <button
                          key={i}
                          onClick={() => handleRunQuery(sq)}
                          className="text-xs bg-white hover:bg-amber-100 text-amber-900 border border-amber-300 px-3 py-1.5 rounded-lg text-left font-medium transition-colors cursor-pointer flex items-center justify-between"
                        >
                          <span>{sq}</span>
                          <ChevronRight className="w-3 h-3 ml-2 text-amber-600" />
                        </button>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {result && result.status === 'success' && (
          <div className="space-y-6 animate-in fade-in duration-300">
            
            {/* Grounded Insight Callout Banner */}
            <div className="bg-gradient-to-r from-blue-900 via-slate-900 to-indigo-950 text-white rounded-2xl p-6 sm:p-7 shadow-lg shadow-blue-900/10 border border-blue-800/50 relative overflow-hidden">
              <div className="absolute right-0 top-0 translate-x-8 -translate-y-8 w-48 h-48 bg-blue-500/10 rounded-full blur-3xl pointer-events-none" />
              
              <div className="flex items-center space-x-2 text-xs font-semibold text-blue-300 tracking-wider uppercase mb-2.5">
                <ShieldCheck className="w-4 h-4 text-emerald-400" />
                <span>Grounded Fact-Checked Insight (Computed From Query Results)</span>
              </div>

              <p className="text-lg sm:text-xl font-medium text-slate-100 leading-snug">
                "{result.insight}"
              </p>

              {/* Statistics Pill Badges */}
              {result.stats && (
                <div className="mt-5 pt-4 border-t border-slate-700/60 flex flex-wrap gap-3 text-xs">
                  {result.stats.count !== undefined && (
                    <div className="bg-slate-800/80 border border-slate-700 px-3 py-1.5 rounded-lg flex items-center space-x-1.5">
                      <span className="text-slate-400">Rows:</span>
                      <span className="font-bold text-slate-100">{result.stats.count}</span>
                    </div>
                  )}
                  {result.stats.average !== undefined && (
                    <div className="bg-slate-800/80 border border-slate-700 px-3 py-1.5 rounded-lg flex items-center space-x-1.5">
                      <span className="text-slate-400">Average:</span>
                      <span className="font-bold text-emerald-400">{result.stats.average}%</span>
                    </div>
                  )}
                  {result.stats.max && (
                    <div className="bg-slate-800/80 border border-slate-700 px-3 py-1.5 rounded-lg flex items-center space-x-1.5">
                      <span className="text-slate-400">Peak:</span>
                      <span className="font-bold text-amber-300">
                        {result.stats.max.value}% {result.stats.max.region ? `(${result.stats.max.region})` : ''}
                      </span>
                    </div>
                  )}
                  {result.stats.min && (
                    <div className="bg-slate-800/80 border border-slate-700 px-3 py-1.5 rounded-lg flex items-center space-x-1.5">
                      <span className="text-slate-400">Low:</span>
                      <span className="font-bold text-blue-300">
                        {result.stats.min.value}% {result.stats.min.region ? `(${result.stats.min.region})` : ''}
                      </span>
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* Visual Chart Card */}
            <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6 sm:p-7">
              <div className="flex items-center justify-between mb-6">
                <div>
                  <h3 className="font-bold text-base sm:text-lg text-slate-900 flex items-center space-x-2">
                    {result.chart.chart_type === 'line' && <LineChartIcon className="w-5 h-5 text-blue-600" />}
                    {result.chart.chart_type === 'bar' && <BarChart3 className="w-5 h-5 text-indigo-600" />}
                    <span>{result.chart.title || 'Data Visualization'}</span>
                  </h3>
                  <p className="text-xs text-slate-500 mt-0.5">
                    Selected by deterministic heuristics based on schema dimensionality
                  </p>
                </div>

                <div className="flex items-center space-x-2">
                  <button
                    onClick={() => setShowDataTable(!showDataTable)}
                    className="text-xs font-medium text-slate-600 hover:text-slate-900 bg-slate-100 hover:bg-slate-200 px-3 py-1.5 rounded-lg transition-colors cursor-pointer flex items-center space-x-1.5"
                  >
                    <TableIcon className="w-3.5 h-3.5" />
                    <span>{showDataTable ? 'Show Chart' : 'View Data Table'}</span>
                  </button>
                </div>
              </div>

              {/* Chart Body */}
              {showDataTable ? (
                <div className="overflow-x-auto max-h-96 border border-slate-200 rounded-xl">
                  <table className="w-full text-left text-xs border-collapse">
                    <thead className="bg-slate-100 sticky top-0 border-b border-slate-200">
                      <tr>
                        {result.raw_data[0] && Object.keys(result.raw_data[0]).map((col) => (
                          <th key={col} className="px-3 py-2 font-semibold text-slate-700 uppercase tracking-wider">
                            {col}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100 bg-white">
                      {result.raw_data.map((row, idx) => (
                        <tr key={idx} className="hover:bg-slate-50">
                          {Object.values(row).map((val, cellIdx) => (
                            <td key={cellIdx} className="px-3 py-2 text-slate-600 whitespace-nowrap">
                              {typeof val === 'number' ? val.toLocaleString() : String(val)}
                            </td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <div className="w-full h-80 sm:h-96">
                  {result.chart.chart_type === 'line' && (
                    <ResponsiveContainer width="100%" height="100%">
                      <LineChart data={result.chart.data} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                        <XAxis dataKey={result.chart.x_key} stroke="#64748b" fontSize={12} tickLine={false} />
                        <YAxis stroke="#64748b" fontSize={12} tickLine={false} tickFormatter={(v) => `${v}%`} />
                        <Tooltip
                          contentStyle={{ backgroundColor: '#0f172a', borderRadius: '8px', color: '#fff', border: 'none' }}
                          labelStyle={{ color: '#94a3b8', fontSize: '11px', marginBottom: '4px' }}
                          formatter={(val) => [`${val}%`, 'Rate']}
                        />
                        <Legend wrapperStyle={{ paddingTop: '10px' }} />
                        {result.chart.y_keys.map((k, idx) => (
                          <Line
                            key={k}
                            type="monotone"
                            dataKey={k}
                            stroke={PALETTE[idx % PALETTE.length]}
                            strokeWidth={2.5}
                            dot={result.chart.data.length < 30}
                            activeDot={{ r: 6 }}
                          />
                        ))}
                      </LineChart>
                    </ResponsiveContainer>
                  )}

                  {result.chart.chart_type === 'bar' && (
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={result.chart.data} margin={{ top: 10, right: 30, left: 0, bottom: 25 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" vertical={false} />
                        <XAxis dataKey={result.chart.x_key} stroke="#64748b" fontSize={11} interval={0} angle={-20} textAnchor="end" />
                        <YAxis stroke="#64748b" fontSize={12} tickLine={false} tickFormatter={(v) => `${v}%`} />
                        <Tooltip
                          contentStyle={{ backgroundColor: '#0f172a', borderRadius: '8px', color: '#fff', border: 'none' }}
                          labelStyle={{ color: '#94a3b8', fontSize: '11px', marginBottom: '4px' }}
                          formatter={(val) => [`${val}%`, 'Unemployment Rate']}
                        />
                        <Bar dataKey={result.chart.y_keys[0]} fill="#2563eb" radius={[6, 6, 0, 0]} />
                      </BarChart>
                    </ResponsiveContainer>
                  )}

                  {result.chart.chart_type === 'kpi' && (
                    <div className="h-full flex flex-col items-center justify-center text-center p-8 bg-slate-50 rounded-xl">
                      <span className="text-xs uppercase font-bold text-slate-500 tracking-wider">
                        {result.chart.kpi_label || 'Calculated Metric'}
                      </span>
                      <div className="text-5xl font-black text-slate-900 mt-2 mb-1">
                        {result.chart.kpi_value}
                        <span className="text-3xl font-medium text-slate-500">{result.chart.kpi_unit}</span>
                      </div>
                      <span className="text-xs text-slate-500">Extracted from ABS Labour Force Series</span>
                    </div>
                  )}

                  {result.chart.chart_type === 'forecast' && (
                    <div className="space-y-4">
                      <div className="bg-purple-50 border border-purple-200 text-purple-900 rounded-xl p-3.5 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2 text-xs">
                        <div className="flex items-center space-x-2">
                          <Sparkles className="w-4 h-4 text-purple-600 shrink-0" />
                          <span className="font-semibold">
                            Statistical Projection: {result.chart.method}
                          </span>
                        </div>
                        <span className="bg-purple-200 text-purple-900 font-bold px-2 py-0.5 rounded text-[11px]">
                          {result.chart.caption}
                        </span>
                      </div>

                      <div className="w-full h-80 sm:h-96">
                        <ResponsiveContainer width="100%" height="100%">
                          <LineChart data={result.chart.data} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
                            <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                            <XAxis dataKey={result.chart.x_key} stroke="#64748b" fontSize={11} tickLine={false} />
                            <YAxis stroke="#64748b" fontSize={12} tickLine={false} tickFormatter={(v) => `${v}%`} domain={['auto', 'auto']} />
                            <Tooltip
                              contentStyle={{ backgroundColor: '#0f172a', borderRadius: '8px', color: '#fff', border: 'none' }}
                              labelStyle={{ color: '#94a3b8', fontSize: '11px', marginBottom: '4px' }}
                              formatter={(val, name) => val !== null && val !== undefined ? [`${val}%`, name] : null}
                            />
                            <Legend wrapperStyle={{ paddingTop: '10px' }} />
                            <Line
                              type="monotone"
                              dataKey="historical_value"
                              name="Observed Rate"
                              stroke="#2563eb"
                              strokeWidth={2.5}
                              dot={false}
                              activeDot={{ r: 5 }}
                              connectNulls={false}
                            />
                            <Line
                              type="monotone"
                              dataKey="ci_95_upper"
                              name="95% CI Upper"
                              stroke="#c084fc"
                              strokeWidth={1}
                              strokeDasharray="2 2"
                              dot={false}
                              connectNulls={false}
                            />
                            <Line
                              type="monotone"
                              dataKey="ci_80_upper"
                              name="80% CI Upper"
                              stroke="#9333ea"
                              strokeWidth={1.5}
                              strokeDasharray="3 3"
                              dot={false}
                              connectNulls={false}
                            />
                            <Line
                              type="monotone"
                              dataKey="projected_mean"
                              name="Projected Mean"
                              stroke="#7e22ce"
                              strokeWidth={3}
                              strokeDasharray="5 5"
                              dot={{ r: 3 }}
                              activeDot={{ r: 6 }}
                              connectNulls={false}
                            />
                            <Line
                              type="monotone"
                              dataKey="ci_80_lower"
                              name="80% CI Lower"
                              stroke="#9333ea"
                              strokeWidth={1.5}
                              strokeDasharray="3 3"
                              dot={false}
                              connectNulls={false}
                            />
                            <Line
                              type="monotone"
                              dataKey="ci_95_lower"
                              name="95% CI Lower"
                              stroke="#c084fc"
                              strokeWidth={1}
                              strokeDasharray="2 2"
                              dot={false}
                              connectNulls={false}
                            />
                          </LineChart>
                        </ResponsiveContainer>
                      </div>

                      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between text-[11px] text-slate-500 pt-2 border-t border-slate-100 gap-1">
                        <span className="font-semibold text-purple-700">
                          ⚠️ {result.chart.caption}
                        </span>
                        <span>
                          Confidence Bands: 80% (inner dashed purple) • 95% (outer dotted lavender)
                        </span>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* SQL & System Guardrails Transparency Drawer */}
            <div className="bg-slate-900 text-slate-100 rounded-2xl p-6 shadow-sm border border-slate-800">
              {/* Reflection Self-Healing Audit Box */}
              {result.reflection_triggered && result.reflection_log && result.reflection_log.length > 0 && (
                <div className="mb-4 p-3.5 bg-emerald-950/60 border border-emerald-800/80 rounded-xl text-xs">
                  <div className="flex items-center space-x-2 text-emerald-400 font-bold uppercase tracking-wider mb-2">
                    <Sparkles className="w-4 h-4 text-emerald-400" />
                    <span>Self-Healing SQL Reflection Active ({result.reflection_log.length} repair attempt)</span>
                  </div>
                  <div className="space-y-2 font-mono text-[11px]">
                    {result.reflection_log.map((log, idx) => (
                      <div key={idx} className="bg-slate-950/80 p-2.5 rounded-lg border border-slate-800 space-y-1">
                        <div className="text-amber-400 font-sans">
                          <strong>Attempt {log.attempt} [{log.trigger}]:</strong> {log.error}
                        </div>
                        <div className="text-slate-400">
                          Initial SQL: <span className="text-rose-300">{log.original_sql}</span>
                        </div>
                        <div className="text-emerald-300">
                          Corrected SQL: <span className="text-emerald-400">{log.corrected_sql}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-4">
                <div className="flex items-center space-x-2">
                  <span className="text-xs font-bold uppercase tracking-wider text-emerald-400 flex items-center">
                    <CheckCircle2 className="w-3.5 h-3.5 mr-1" />
                    SQL Validation & Guardrail Status
                  </span>
                  {result.reflection_triggered && (
                    <span className="bg-emerald-800/60 text-emerald-300 border border-emerald-600 px-2 py-0.5 rounded text-[10px] font-bold">
                      Self-Healed
                    </span>
                  )}
                </div>

                <div className="flex items-center space-x-3 text-xs text-slate-400">
                  <span className="flex items-center">
                    <Clock className="w-3.5 h-3.5 mr-1 text-slate-500" />
                    {result.execution_time_ms} ms
                  </span>
                  <span>•</span>
                  <span>{result.row_count} rows</span>
                  <span>•</span>
                  <span>Model: <code className="text-blue-300 font-mono">{result.model_used}</code></span>
                </div>
              </div>

              {/* SQL Display Box */}
              <div className="relative group">
                <pre className="bg-slate-950 p-4 rounded-xl text-xs font-mono text-blue-200 overflow-x-auto border border-slate-800 leading-relaxed">
                  {result.sql}
                </pre>
                <button
                  onClick={() => copyToClipboard(result.sql)}
                  className="absolute right-3 top-3 p-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg text-xs font-medium flex items-center space-x-1 transition-colors cursor-pointer border border-slate-700"
                >
                  {copiedSQL ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                  <span>{copiedSQL ? 'Copied' : 'Copy SQL'}</span>
                </button>
              </div>

              {/* Guardrail Checklist */}
              <div className="mt-4 pt-4 border-t border-slate-800 grid grid-cols-2 sm:grid-cols-4 gap-2 text-[11px] text-slate-400">
                <div className="flex items-center space-x-1.5">
                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                  <span>sqlglot AST Validated</span>
                </div>
                <div className="flex items-center space-x-1.5">
                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                  <span>Single SELECT Enforced</span>
                </div>
                <div className="flex items-center space-x-1.5">
                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                  <span>Row Cap: 1000 Max</span>
                </div>
                <div className="flex items-center space-x-1.5">
                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                  <span>Query Timeout: 3.0s</span>
                </div>
              </div>
            </div>

          </div>
        )}

      </main>

      {/* Settings Modal */}
      {showSettings && (
        <div className="fixed inset-0 bg-slate-900/50 backdrop-blur-xs z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-md w-full p-6 shadow-xl border border-slate-200 animate-in fade-in zoom-in-95 duration-200">
            <div className="flex items-center justify-between pb-4 border-b border-slate-100">
              <div className="flex items-center space-x-2">
                <Settings2 className="w-5 h-5 text-blue-600" />
                <h3 className="font-bold text-slate-900">LLM Provider Configuration</h3>
              </div>
              <button
                onClick={() => setShowSettings(false)}
                className="text-slate-400 hover:text-slate-600 p-1 rounded-lg cursor-pointer"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleSaveSettings} className="space-y-4 mt-4 text-sm">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  OpenRouter API Key (Optional)
                </label>
                <input
                  type="password"
                  value={apiKey}
                  onChange={(e) => setApiKey(e.target.value)}
                  placeholder="sk-or-v1-..."
                  className="w-full px-3.5 py-2.5 bg-slate-50 border border-slate-300 rounded-lg text-xs font-mono focus:outline-none focus:ring-2 focus:ring-blue-600 focus:bg-white"
                />
                <p className="text-[11px] text-slate-500 mt-1">
                  If left empty, the built-in deterministic engine is used with 100% test coverage.
                </p>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Model Identifier
                </label>
                <input
                  type="text"
                  value={model}
                  onChange={(e) => setModel(e.target.value)}
                  placeholder="meta-llama/llama-3.3-70b-instruct:free"
                  className="w-full px-3.5 py-2.5 bg-slate-50 border border-slate-300 rounded-lg text-xs font-mono focus:outline-none focus:ring-2 focus:ring-blue-600 focus:bg-white"
                />
                <p className="text-[11px] text-slate-500 mt-1">
                  Default: <code className="bg-slate-100 px-1 py-0.5 rounded">meta-llama/llama-3.3-70b-instruct:free</code> or any OpenRouter model.
                </p>
              </div>

              <div className="pt-4 border-t border-slate-100 flex justify-end space-x-2">
                <button
                  type="button"
                  onClick={() => setShowSettings(false)}
                  className="px-4 py-2 text-xs font-medium text-slate-600 hover:bg-slate-100 rounded-lg cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 text-xs font-bold text-white bg-blue-600 hover:bg-blue-700 rounded-lg shadow-sm cursor-pointer"
                >
                  Save Settings
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Footer */}
      <footer className="border-t border-slate-200 bg-white py-6 mt-12 text-xs text-slate-500">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between gap-4">
          <div>
            Aus Gov Data Explorer • Portfolio Project 3 • Built with FastAPI, SQLite, React, sqlglot & OpenRouter
          </div>
          <div className="flex items-center space-x-4">
            <a
              href="https://www.abs.gov.au/statistics/labour/employment-and-unemployment/labour-force-australia/"
              target="_blank"
              rel="noreferrer"
              className="hover:text-blue-600 flex items-center"
            >
              <span>ABS Source Catalogue 6202.0</span>
              <ExternalLink className="w-3 h-3 ml-1" />
            </a>
          </div>
        </div>
      </footer>
    </div>
  );
}
