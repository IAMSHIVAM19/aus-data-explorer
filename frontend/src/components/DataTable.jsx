import React, { memo } from 'react';

const DataTable = memo(({ data }) => {
  if (!data || data.length === 0) return null;

  const columns = Object.keys(data[0]);

  return (
    <div className="overflow-x-auto max-h-96 border border-slate-200 rounded-xl">
      <table className="w-full text-left text-xs border-collapse">
        <thead className="bg-slate-100 sticky top-0 border-b border-slate-200">
          <tr>
            {columns.map((col) => (
              <th key={col} className="px-3 py-2 font-semibold text-slate-700 uppercase tracking-wider">
                {col}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100 bg-white">
          {data.map((row, idx) => (
            <tr key={idx} className="hover:bg-slate-50">
              {columns.map((col) => {
                const val = row[col];
                return (
                  <td key={col} className="px-3 py-2 text-slate-600 whitespace-nowrap">
                    {val === null || val === undefined ? '—' : (typeof val === 'number' ? val.toLocaleString() : String(val))}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
});

export default DataTable;
