import React, { useMemo } from 'react';
import { ChevronRight } from 'lucide-react';

export default function SeedQuestions({ questions, categories, activeCategory, onCategoryChange, onQuestionClick }) {
  const filteredQuestions = useMemo(() => {
    return questions.filter(q => {
      if (activeCategory === 'all') return true;
      return q.category === activeCategory;
    });
  }, [questions, activeCategory]);

  return (
    <div className="mt-8 pt-6 border-t border-slate-100">
      <div className="flex items-center justify-between flex-wrap gap-2 mb-3">
        <span className="text-xs font-bold uppercase tracking-wider text-slate-500">
          Explore Seed Questions (15+ Pre-configured Scenarios):
        </span>
        
        <div className="flex flex-wrap gap-1">
          {categories.map(cat => (
            <button
              key={cat.id}
              onClick={() => onCategoryChange(cat.id)}
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
            onClick={() => onQuestionClick(item.question)}
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
  );
}
