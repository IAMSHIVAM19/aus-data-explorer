import { useState, useEffect } from 'react';

export default function useQueryApi() {
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [seedQuestions, setSeedQuestions] = useState([]);
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
      .catch(err => console.error('Error fetching health info:', err));

    fetch('/api/seed-questions')
      .then(res => res.json())
      .then(data => {
        if (data.questions) setSeedQuestions(data.questions);
      })
      .catch(err => console.error('Error fetching seed questions:', err));
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

  return {
    query,
    setQuery,
    loading,
    error,
    result,
    seedQuestions,
    healthInfo,
    handleRunQuery,
    copiedSQL,
    copyToClipboard,
    apiKey,
    setApiKey,
    model,
    setModel,
    showSettings,
    setShowSettings,
    handleSaveSettings,
    showDataTable,
    setShowDataTable
  };
}
