import React, { useState } from 'react';
import {
  ShieldCheck, ShieldAlert, Clock, CheckCircle2, AlertTriangle, HelpCircle,
  BarChart3, LineChart as LineChartIcon, Table as TableIcon,
  Copy, Check, ExternalLink, ChevronRight
} from 'lucide-react';

import Header from './components/Header';
import SearchForm from './components/SearchForm';
import SeedQuestions from './components/SeedQuestions';
import ChartRenderer from './components/ChartRenderer';
import DataTable from './components/DataTable';
import SettingsModal from './components/SettingsModal';
import ErrorBoundary from './components/ErrorBoundary';
import useQueryApi from './hooks/useQueryApi';

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

function AppContent() {
  const {
    query, setQuery, loading, error, result, seedQuestions, healthInfo,
    handleRunQuery, copiedSQL, copyToClipboard,
    apiKey, setApiKey, model, setModel, showSettings, setShowSettings,
    handleSaveSettings, showDataTable, setShowDataTable
  } = useQueryApi();

  const [activeCategory, setActiveCategory] = useState('all');

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 flex flex-col font-sans">
      <Header apiKey={apiKey} onOpenSettings={() => setShowSettings(true)} healthInfo={healthInfo} />

      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
        <section className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6 sm:p-8 relative overflow-hidden">
          <SearchForm 
            query={query} 
            onQueryChange={setQuery} 
            onSubmit={() => handleRunQuery()} 
            loading={loading} 
          />
          <SeedQuestions 
            questions={seedQuestions}
            categories={categories}
            activeCategory={activeCategory}
            onCategoryChange={setActiveCategory}
            onQuestionClick={handleRunQuery}
          />
        </section>

        {error && (
          <div className="bg-rose-50 border border-rose-200 rounded-2xl p-6 text-rose-800 flex items-start space-x-3">
            <AlertTriangle className="w-5 h-5 text-rose-600 shrink-0 mt-0.5" />
            <div>
              <h3 className="font-bold text-sm">Query Failed</h3>
              <p className="text-xs text-rose-700 mt-1">{error}</p>
            </div>
          </div>
        )}

        {result && (result.status === 'validation_error' || result.status === 'execution_error') && (
          <div className="bg-rose-50 border border-rose-200 rounded-2xl p-6 text-rose-950 shadow-sm animate-in fade-in duration-300">
            <div className="flex items-start space-x-3.5">
              <div className="p-2 bg-rose-100 rounded-xl text-rose-700 shrink-0">
                <ShieldAlert className="w-6 h-6" />
              </div>
              <div className="flex-1">
                <div className="flex items-center space-x-2">
                  <span className="text-xs font-bold uppercase tracking-wider bg-rose-200 text-rose-900 px-2 py-0.5 rounded">
                    Security Guardrail Activated: {result.status === 'validation_error' ? 'SQL AST Validation' : 'Execution Engine'}
                  </span>
                  <span className="text-xs text-rose-700 font-medium">
                    (Stopped safely after retry limit)
                  </span>
                </div>
                <p className="text-sm font-semibold text-rose-950 mt-2 leading-relaxed">
                  {result.error}
                </p>
                <p className="text-xs text-rose-800 mt-1">
                  The query referenced unauthorized tables, unsupported syntax, or exceeded execution constraints. The self-healing reflection loop attempted repair but halted to guarantee database security.
                </p>

                {result.reflection_log && result.reflection_log.length > 0 && (
                  <div className="mt-4 pt-4 border-t border-rose-200">
                    <span className="text-xs font-semibold text-rose-900 uppercase tracking-wider block mb-2">
                      Reflection & Diagnostics History ({result.reflection_log.length} attempts):
                    </span>
                    <div className="space-y-2">
                      {result.reflection_log.map((log, i) => (
                        <div key={i} className="text-xs bg-white/80 border border-rose-200 p-2.5 rounded-lg text-rose-900">
                          <div className="font-semibold text-[11px] text-rose-800">
                            Attempt {log.attempt || i + 1} Trigger: <span className="font-mono">{log.trigger}</span>
                          </div>
                          <div className="text-[11px] text-rose-700 mt-0.5">
                            {log.error_message || log.error || 'Validation check failed'}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
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
            <div className="bg-gradient-to-r from-blue-900 via-slate-900 to-indigo-950 text-white rounded-2xl p-6 sm:p-7 shadow-lg shadow-blue-900/10 border border-blue-800/50 relative overflow-hidden">
              <div className="absolute right-0 top-0 translate-x-8 -translate-y-8 w-48 h-48 bg-blue-500/10 rounded-full blur-3xl pointer-events-none" />
              
              <div className="flex items-center space-x-2 text-xs font-semibold text-blue-300 tracking-wider uppercase mb-2.5">
                <ShieldCheck className="w-4 h-4 text-emerald-400" />
                <span>Grounded Fact-Checked Insight (Computed From Query Results)</span>
              </div>

              <p className="text-lg sm:text-xl font-medium text-slate-100 leading-snug">
                "{result.insight}"
              </p>

              {result.is_forecast && result.stats ? (
                <div className="mt-5 pt-4 border-t border-slate-700/60 flex flex-wrap gap-3 text-xs">
                  <div className="bg-slate-800/80 border border-slate-700 px-3 py-1.5 rounded-lg flex items-center space-x-1.5">
                    <span className="text-slate-400">Method:</span>
                    <span className="font-bold text-slate-100">{result.stats.forecast_method}</span>
                  </div>
                  {result.stats.last_observed_value !== undefined && (
                    <div className="bg-slate-800/80 border border-slate-700 px-3 py-1.5 rounded-lg flex items-center space-x-1.5">
                      <span className="text-slate-400">Last Actual ({result.stats.last_observed_date}):</span>
                      <span className="font-bold text-blue-300">{result.stats.last_observed_value}%</span>
                    </div>
                  )}
                  {result.stats.projected_final_value !== undefined && (
                    <div className="bg-slate-800/80 border border-slate-700 px-3 py-1.5 rounded-lg flex items-center space-x-1.5">
                      <span className="text-slate-400">Projected ({result.stats.projected_final_date}):</span>
                      <span className="font-bold text-purple-300">{result.stats.projected_final_value}%</span>
                    </div>
                  )}
                  {result.stats.ci_80 && (
                    <div className="bg-slate-800/80 border border-slate-700 px-3 py-1.5 rounded-lg flex items-center space-x-1.5">
                      <span className="text-slate-400">80% CI:</span>
                      <span className="font-bold text-emerald-400">{result.stats.ci_80[0]}% – {result.stats.ci_80[1]}%</span>
                    </div>
                  )}
                </div>
              ) : result.stats && (
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
                      <span className="font-bold text-emerald-400">
                        {result.chart?.unit ? `${result.stats.average}${result.chart.unit}` : result.stats.average.toLocaleString()}
                      </span>
                    </div>
                  )}
                  {result.stats.max && (
                    <div className="bg-slate-800/80 border border-slate-700 px-3 py-1.5 rounded-lg flex items-center space-x-1.5">
                      <span className="text-slate-400">Peak:</span>
                      <span className="font-bold text-amber-300">
                        {result.chart?.unit ? `${result.stats.max.value}${result.chart.unit}` : result.stats.max.value.toLocaleString()} {result.stats.max.region ? `(${result.stats.max.region})` : ''}
                      </span>
                    </div>
                  )}
                  {result.stats.min && (
                    <div className="bg-slate-800/80 border border-slate-700 px-3 py-1.5 rounded-lg flex items-center space-x-1.5">
                      <span className="text-slate-400">Low:</span>
                      <span className="font-bold text-blue-300">
                        {result.chart?.unit ? `${result.stats.min.value}${result.chart.unit}` : result.stats.min.value.toLocaleString()} {result.stats.min.region ? `(${result.stats.min.region})` : ''}
                      </span>
                    </div>
                  )}
                </div>
              )}
            </div>

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

              {showDataTable ? (
                <DataTable data={result.raw_data} />
              ) : (
                <div className="w-full h-80 sm:h-96">
                  <ChartRenderer chart={result.chart} />
                </div>
              )}
            </div>

            <div className="bg-slate-900 text-slate-100 rounded-2xl p-6 shadow-sm border border-slate-800">
              {result.reflection_triggered && result.reflection_log && result.reflection_log.length > 0 && (
                <div className="mb-4 p-3.5 bg-emerald-950/60 border border-emerald-800/80 rounded-xl text-xs">
                  <div className="flex items-center space-x-2 text-emerald-400 font-bold uppercase tracking-wider mb-2">
                    <ShieldCheck className="w-4 h-4 text-emerald-400" />
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

      <SettingsModal 
        show={showSettings}
        onClose={() => setShowSettings(false)}
        apiKey={apiKey}
        onApiKeyChange={setApiKey}
        model={model}
        onModelChange={setModel}
        onSave={handleSaveSettings}
      />

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

export default function App() {
  return (
    <ErrorBoundary>
      <AppContent />
    </ErrorBoundary>
  );
}
