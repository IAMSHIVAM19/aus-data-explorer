import React from 'react';
import { Search, Sparkles } from 'lucide-react';

export default function SearchForm({ query, onQueryChange, onSubmit, loading }) {
  return (
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
          onSubmit();
        }}
        className="flex flex-col sm:flex-row gap-2.5"
      >
        <div className="relative flex-1">
          <Search className="w-5 h-5 absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            type="text"
            value={query}
            onChange={(e) => onQueryChange(e.target.value)}
            placeholder="e.g. Compare unemployment rate trends between NSW and Victoria"
            aria-label="Search query"
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
  );
}
