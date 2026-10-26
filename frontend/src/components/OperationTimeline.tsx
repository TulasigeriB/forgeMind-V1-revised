import React from 'react';
import type { ProcessOperation } from '../services/api';

interface OperationTimelineProps {
  operations: ProcessOperation[];
}

const OperationTimeline: React.FC<OperationTimelineProps> = ({ operations }) => {
  const sortedOps = [...operations].sort((a, b) => a.sequence_order - b.sequence_order);

  return (
    <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
      <div className="mb-6">
        <h3 className="text-lg font-bold text-slate-800">Manufacturing Sequence</h3>
        <p className="text-xs text-slate-500">Optimized production routing</p>
      </div>
      <div className="relative space-y-6">
        {sortedOps.map((op, idx) => (
          <div key={op.id} className="relative pl-8">
            {/* Timeline Line */}
            {idx !== sortedOps.length - 1 && (
              <div className="absolute left-3 top-6 w-0.5 h-full bg-slate-200" />
            )}
            {/* Timeline Dot */}
            <div className="absolute left-0 top-1 w-6 h-6 bg-blue-600 border-4 border-white rounded-full shadow-sm z-10" />

            <div className="p-4 bg-slate-50 rounded-lg border border-slate-200 hover:border-blue-300 transition-all group">
              <div className="flex justify-between items-start mb-2">
                <div>
                  <span className="text-xs font-bold text-blue-600 uppercase tracking-wider">Op {op.sequence_order}</span>
                  <h4 className="font-bold text-slate-800 group-hover:text-blue-700">{op.operation_name}</h4>
                </div>
                <div className="text-right">
                  <p className="text-sm font-bold text-slate-700">${op.estimated_cost.toFixed(2)} / part</p>
                  <p className="text-xs text-slate-500">
                    {op.estimated_time_minutes > 0 ? `${op.estimated_time_minutes} mins / part` : 'Cycle time not estimated'}
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-2 mt-3">
                <span className="px-2 py-0.5 bg-white border border-slate-200 rounded text-[10px] font-semibold text-slate-600 uppercase">
                  {op.machine_type ?? 'Machine not specified'}
                </span>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default OperationTimeline;
