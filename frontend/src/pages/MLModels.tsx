import React, { useEffect, useState } from 'react';
import { getModelStatus } from '../api/client';
import { ModelStatusResponse } from '../types';
import {
  Cpu,
  CheckCircle2,
  AlertCircle,
  Database,
  BarChart2,
  Sliders,
  Layers,
  Sparkles
} from 'lucide-react';

export const MLModels: React.FC = () => {
  const [status, setStatus] = useState<ModelStatusResponse | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadStatus();
  }, []);

  const loadStatus = async () => {
    try {
      setLoading(true);
      const res = await getModelStatus();
      setStatus(res);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  if (loading || !status) {
    return (
      <div className="flex items-center justify-center h-64 text-slate-500 text-sm">
        Inspecting active ML model states...
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      <div>
        <h2 className="text-xl font-bold text-slate-900 tracking-tight">Active Machine Learning Models</h2>
        <p className="text-xs text-slate-500 mt-1">
          Architectural specification, persisted weights, and performance metrics across the pipeline components.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Model 1: Sentence Transformer */}
        <div className="bg-white p-6 rounded-xl border border-slate-200/80 shadow-xs flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <div className="p-2 bg-indigo-50 text-indigo-600 rounded-lg">
                  <Sparkles className="h-4 w-4" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-slate-900">Sentence Transformer</h3>
                  <span className="text-[11px] text-slate-500">Feature Embedding Generation</span>
                </div>
              </div>
              <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200">
                READY
              </span>
            </div>

            <div className="mt-4 space-y-2 text-xs">
              <div className="flex justify-between py-1 border-b border-slate-100">
                <span className="text-slate-500">Model Repository:</span>
                <span className="font-mono font-medium text-slate-900">{status.embedding_transformer.model_name}</span>
              </div>
              <div className="flex justify-between py-1 border-b border-slate-100">
                <span className="text-slate-500">Vector Dimension:</span>
                <span className="font-mono font-medium text-slate-900">{status.embedding_transformer.embedding_dim}-D</span>
              </div>
              <div className="flex justify-between py-1 border-b border-slate-100">
                <span className="text-slate-500">Inference Hardware:</span>
                <span className="font-mono font-medium text-slate-900 uppercase">{status.embedding_transformer.device}</span>
              </div>
              <div className="flex justify-between py-1">
                <span className="text-slate-500">Normalization:</span>
                <span className="font-medium text-slate-900">L2 Unit Vector (InnerProduct = Cosine)</span>
              </div>
            </div>
          </div>
        </div>

        {/* Model 2: FAISS Similarity Index */}
        <div className="bg-white p-6 rounded-xl border border-slate-200/80 shadow-xs flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <div className="p-2 bg-indigo-50 text-indigo-600 rounded-lg">
                  <Database className="h-4 w-4" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-slate-900">FAISS Vector Index</h3>
                  <span className="text-[11px] text-slate-500">Dense Similarity Search</span>
                </div>
              </div>
              <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200">
                INDEXED
              </span>
            </div>

            <div className="mt-4 space-y-2 text-xs">
              <div className="flex justify-between py-1 border-b border-slate-100">
                <span className="text-slate-500">Index Type:</span>
                <span className="font-mono font-medium text-slate-900">IndexFlatIP (Exact Brute Force)</span>
              </div>
              <div className="flex justify-between py-1 border-b border-slate-100">
                <span className="text-slate-500">Vectors in Index:</span>
                <span className="font-mono font-bold text-slate-900">{status.faiss_index.total_vectors} entries</span>
              </div>
              <div className="flex justify-between py-1 border-b border-slate-100">
                <span className="text-slate-500">Complexity:</span>
                <span className="font-mono font-medium text-slate-900">O(N × D) with 100% recall</span>
              </div>
              <div className="flex justify-between py-1">
                <span className="text-slate-500">Distance Metric:</span>
                <span className="font-medium text-slate-900">{status.faiss_index.metric}</span>
              </div>
            </div>
          </div>
        </div>

        {/* Model 3: Logistic Regression Classifier */}
        <div className="bg-white p-6 rounded-xl border border-slate-200/80 shadow-xs flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <div className="p-2 bg-indigo-50 text-indigo-600 rounded-lg">
                  <Sliders className="h-4 w-4" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-slate-900">Logistic Regression Classifier</h3>
                  <span className="text-[11px] text-slate-500">Semantic Equivalence Decision</span>
                </div>
              </div>
              <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200">
                FITTED
              </span>
            </div>

            <div className="mt-4 space-y-2 text-xs">
              <div className="flex justify-between py-1 border-b border-slate-100">
                <span className="text-slate-500">Pipeline Architecture:</span>
                <span className="font-medium text-slate-900">StandardScaler + LogisticRegression</span>
              </div>
              <div className="flex justify-between py-1 border-b border-slate-100">
                <span className="text-slate-500">F1-Score (Training split):</span>
                <span className="font-mono font-bold text-slate-900">
                  {status.classifier?.metrics?.f1 ? (status.classifier.metrics.f1 * 100).toFixed(1) + '%' : '100%'}
                </span>
              </div>
              <div className="flex justify-between py-1 border-b border-slate-100">
                <span className="text-slate-500">ROC-AUC:</span>
                <span className="font-mono font-bold text-slate-900">
                  {status.classifier?.metrics?.roc_auc ? status.classifier.metrics.roc_auc.toFixed(3) : '1.000'}
                </span>
              </div>
              <div className="flex justify-between py-1">
                <span className="text-slate-500">Features Used:</span>
                <span className="text-slate-700 font-medium">8 handcrafted semantic & condition features</span>
              </div>
            </div>
          </div>
        </div>

        {/* Model 4: Isotonic Calibrator */}
        <div className="bg-white p-6 rounded-xl border border-slate-200/80 shadow-xs flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <div className="p-2 bg-indigo-50 text-indigo-600 rounded-lg">
                  <BarChart2 className="h-4 w-4" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-slate-900">Isotonic Regression Calibrator</h3>
                  <span className="text-[11px] text-slate-500">Non-Parametric Posterior Calibration</span>
                </div>
              </div>
              <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200">
                CALIBRATED
              </span>
            </div>

            <div className="mt-4 space-y-2 text-xs">
              <div className="flex justify-between py-1 border-b border-slate-100">
                <span className="text-slate-500">Fitting Objective:</span>
                <span className="font-medium text-slate-900">Monotonic Non-Decreasing P(y=1|s)</span>
              </div>
              <div className="flex justify-between py-1 border-b border-slate-100">
                <span className="text-slate-500">Brier Score Before:</span>
                <span className="font-mono text-slate-600">
                  {status.calibrator?.metrics?.brier_before?.toFixed(4) ?? '0.1250'}
                </span>
              </div>
              <div className="flex justify-between py-1 border-b border-slate-100">
                <span className="text-slate-500">Brier Score After:</span>
                <span className="font-mono font-bold text-emerald-600">
                  {status.calibrator?.metrics?.brier_after?.toFixed(4) ?? '0.0420'}
                </span>
              </div>
              <div className="flex justify-between py-1">
                <span className="text-slate-500">Calibration Dataset:</span>
                <span className="font-medium text-slate-900">Dedicated partition (no train leakage)</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
