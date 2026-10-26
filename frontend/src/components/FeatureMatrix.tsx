import React from 'react';
import type { Feature } from '../services/api';

interface FeatureMatrixProps {
  features: Feature[];
}

const FeatureMatrix: React.FC<FeatureMatrixProps> = ({ features }) => {
  return (
    <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
      <div className="px-6 py-4 border-b border-slate-200 bg-slate-50">
        <h3 className="text-lg font-bold text-slate-800">Geometric Feature Matrix</h3>
        <p className="text-xs text-slate-500">Extracted dimensions and precision requirements</p>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-left text-sm">
          <thead className="bg-slate-50 text-slate-600 uppercase text-xs font-semibold">
            <tr>
              <th className="px-6 py-3">Feature Type</th>
              <th className="px-6 py-3">Dimension (mm)</th>
              <th className="px-6 py-3">Tolerance</th>
              <th className="px-6 py-3">Qty</th>
              <th className="px-6 py-3">Complexity</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {features.map((f) => (
              <tr key={f.id} className="hover:bg-blue-50 transition-colors">
                <td className="px-6 py-4 font-medium text-slate-700">{f.feature_type}</td>
                <td className="px-6 py-4 text-slate-600">{f.dimension ?? '—'}</td>
                <td className="px-6 py-4">
                  <span className={`px-2 py-1 rounded-full text-xs font-bold ${
                    f.tolerance && f.tolerance !== 'standard' ? 'bg-amber-100 text-amber-700' : 'bg-slate-100 text-slate-600'
                  }`}>
                    {f.tolerance ?? 'Unspecified'}
                  </span>
                </td>
                <td className="px-6 py-4 text-slate-600">{f.quantity}</td>
                <td className="px-6 py-4">
                  <div className="flex gap-1">
                    {[1, 2, 3].map((i) => (
                      <div key={i} className={`h-1.5 w-4 rounded-full ${
                        i <= (f.tolerance && f.tolerance !== 'standard' ? 3 : 1) ? 'bg-blue-500' : 'bg-slate-200'
                      }`} />
                    ))}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default FeatureMatrix;
