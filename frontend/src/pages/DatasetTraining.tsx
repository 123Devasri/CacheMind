import React, { useEffect, useState } from 'react';
import { triggerModelTraining } from '../api/client';
import {
  GraduationCap,
  Play,
  CheckCircle,
  FileSpreadsheet,
  Layers,
  ArrowRight
} from 'lucide-react';

export const DatasetTraining: React.FC = () => {
  const [training, setTraining] = useState(false);
  const [trainResult, setTrainResult] = useState<any>(null);

  const handleTrain = async () => {
    try {
      setTraining(true);
      const res = await triggerModelTraining();
      setTrainResult(res.results);
    } catch (err) {
      console.error(err);
    } finally {
      setTraining(false);
    }
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-slate-900 tracking-tight">Dataset Management & Training Pipeline</h2>
          <p className="text-xs text-slate-500 mt-1">
            Group-stratified dataset partitions, training Logistic Regression, and Isotonic Calibration.
          </p>
        </div>

        <button
          onClick={handleTrain}
          disabled={training}
          className="inline-flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold rounded-lg shadow-sm transition disabled:opacity-50 cursor-pointer"
        >
          <Play className="h-3.5 w-3.5 fill-current" />
          <span>{training ? 'Training Pipeline Running...' : 'Train Models & Calibrate'}</span>
        </button>
      </div>

      {/* Dataset Partitions Summary */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-white p-5 rounded-xl border border-slate-200/80 shadow-xs">
          <div className="text-xs font-medium text-slate-500">Train Split (60%)</div>
          <div className="text-xl font-bold text-slate-900 mt-2">22 Pairs</div>
          <div className="text-[11px] text-slate-400 mt-1">Trains Logistic Regression</div>
        </div>

        <div className="bg-white p-5 rounded-xl border border-slate-200/80 shadow-xs">
          <div className="text-xs font-medium text-slate-500">Calibration Split (20%)</div>
          <div className="text-xl font-bold text-slate-900 mt-2">10 Pairs</div>
          <div className="text-[11px] text-slate-400 mt-1">Fits Isotonic Regressor</div>
        </div>

        <div className="bg-white p-5 rounded-xl border border-slate-200/80 shadow-xs">
          <div className="text-xs font-medium text-slate-500">Validation Split (10%)</div>
          <div className="text-xl font-bold text-slate-900 mt-2">6 Pairs</div>
          <div className="text-[11px] text-slate-400 mt-1">Threshold FHR evaluation</div>
        </div>

        <div className="bg-white p-5 rounded-xl border border-slate-200/80 shadow-xs">
          <div className="text-xs font-medium text-slate-500">Test Split (10%)</div>
          <div className="text-xl font-bold text-slate-900 mt-2">7 Pairs</div>
          <div className="text-[11px] text-slate-400 mt-1">Final untouched generalization</div>
        </div>
      </div>

      {/* Group-Leakage Safety Banner */}
      <div className="bg-indigo-50/50 border border-indigo-200 p-4 rounded-xl flex items-center justify-between text-xs text-indigo-900">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-indigo-100 rounded-lg text-indigo-700">
            <Layers className="h-4 w-4" />
          </div>
          <div>
            <span className="font-semibold block">Semantic Group-Level Stratification Enforced</span>
            <span className="text-indigo-700">
              Questions regarding the same underlying policy fact are kept strictly within the same partition to prevent memorization leakage.
            </span>
          </div>
        </div>
      </div>

      {/* Training Results Details */}
      {trainResult && (
        <div className="bg-white p-6 rounded-xl border border-slate-200/80 shadow-xs space-y-4">
          <h3 className="text-sm font-bold text-slate-900">Execution Summary</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
            <div className="p-4 bg-slate-50 rounded-lg border border-slate-200 space-y-2">
              <span className="font-semibold text-slate-800 block">Classifier Metrics:</span>
              <div className="flex justify-between">
                <span className="text-slate-500">Precision:</span>
                <span className="font-mono font-bold text-slate-900">{(trainResult.classifier.metrics.precision * 100).toFixed(1)}%</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">Recall:</span>
                <span className="font-mono font-bold text-slate-900">{(trainResult.classifier.metrics.recall * 100).toFixed(1)}%</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">ROC-AUC:</span>
                <span className="font-mono font-bold text-slate-900">{trainResult.classifier.metrics.roc_auc.toFixed(3)}</span>
              </div>
            </div>

            <div className="p-4 bg-slate-50 rounded-lg border border-slate-200 space-y-2">
              <span className="font-semibold text-slate-800 block">Calibration Improvement:</span>
              <div className="flex justify-between">
                <span className="text-slate-500">Brier Before:</span>
                <span className="font-mono text-slate-600">{trainResult.calibrator.brier_score_before.toFixed(4)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">Brier After:</span>
                <span className="font-mono font-bold text-emerald-600">{trainResult.calibrator.brier_score_after.toFixed(4)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">Selected Threshold:</span>
                <span className="font-mono font-bold text-indigo-600">{trainResult.threshold_evaluation.selected_threshold}</span>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
