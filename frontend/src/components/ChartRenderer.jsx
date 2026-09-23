import React, { memo } from 'react';
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
import { Sparkles } from 'lucide-react';

const PALETTE = ['#2563eb', '#10b981', '#f59e0b', '#ec4899', '#8b5cf6', '#06b6d4', '#f97316', '#64748b'];

const ChartRenderer = memo(({ chart }) => {
  const unit = chart.unit || '';
  const formatVal = (v) => {
    if (v === null || v === undefined) return '';
    return unit ? `${v}${unit}` : Number(v).toLocaleString();
  };

  if (chart.chart_type === 'line') {
    return (
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={chart.data} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
          <XAxis dataKey={chart.x_key} stroke="#64748b" fontSize={12} tickLine={false} />
          <YAxis stroke="#64748b" fontSize={12} tickLine={false} tickFormatter={formatVal} />
          <Tooltip
            contentStyle={{ backgroundColor: '#0f172a', borderRadius: '8px', color: '#fff', border: 'none' }}
            labelStyle={{ color: '#94a3b8', fontSize: '11px', marginBottom: '4px' }}
            formatter={(val, name) => [formatVal(val), name || 'Value']}
          />
          <Legend wrapperStyle={{ paddingTop: '10px' }} />
          {chart.y_keys.map((k, idx) => (
            <Line
              key={k}
              type="monotone"
              dataKey={k}
              stroke={PALETTE[idx % PALETTE.length]}
              strokeWidth={2.5}
              dot={chart.data.length < 30}
              activeDot={{ r: 6 }}
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    );
  }

  if (chart.chart_type === 'bar') {
    return (
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={chart.data} margin={{ top: 10, right: 30, left: 0, bottom: 25 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" vertical={false} />
          <XAxis dataKey={chart.x_key} stroke="#64748b" fontSize={11} interval={0} angle={-20} textAnchor="end" />
          <YAxis stroke="#64748b" fontSize={12} tickLine={false} tickFormatter={formatVal} />
          <Tooltip
            contentStyle={{ backgroundColor: '#0f172a', borderRadius: '8px', color: '#fff', border: 'none' }}
            labelStyle={{ color: '#94a3b8', fontSize: '11px', marginBottom: '4px' }}
            formatter={(val, name) => [formatVal(val), name || 'Value']}
          />
          <Bar dataKey={chart.y_keys[0]} fill="#2563eb" radius={[6, 6, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    );
  }

  if (chart.chart_type === 'kpi') {
    return (
      <div className="h-full flex flex-col items-center justify-center text-center p-8 bg-slate-50 rounded-xl">
        <span className="text-xs uppercase font-bold text-slate-500 tracking-wider">
          {chart.kpi_label || 'Calculated Metric'}
        </span>
        <div className="text-5xl font-black text-slate-900 mt-2 mb-1">
          {chart.kpi_value}
          <span className="text-3xl font-medium text-slate-500">{chart.kpi_unit}</span>
        </div>
        <span className="text-xs text-slate-500">Extracted from ABS Labour Force Series</span>
      </div>
    );
  }

  if (chart.chart_type === 'forecast') {
    return (
      <div className="space-y-4 h-full flex flex-col">
        <div className="bg-purple-50 border border-purple-200 text-purple-900 rounded-xl p-3.5 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2 text-xs">
          <div className="flex items-center space-x-2">
            <Sparkles className="w-4 h-4 text-purple-600 shrink-0" />
            <span className="font-semibold">
              Statistical Projection: {chart.method}
            </span>
          </div>
          <span className="bg-purple-200 text-purple-900 font-bold px-2 py-0.5 rounded text-[11px]">
            {chart.caption}
          </span>
        </div>

        <div className="w-full flex-1 min-h-0">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={chart.data} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
              <XAxis dataKey={chart.x_key} stroke="#64748b" fontSize={11} tickLine={false} />
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

        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between text-[11px] text-slate-500 pt-2 border-t border-slate-100 gap-1 mt-auto">
          <span className="font-semibold text-purple-700">
            ⚠️ {chart.caption}
          </span>
          <span>
            Confidence Bands: 80% (inner dashed purple) • 95% (outer dotted lavender)
          </span>
        </div>
      </div>
    );
  }

  return null;
});

export default ChartRenderer;
