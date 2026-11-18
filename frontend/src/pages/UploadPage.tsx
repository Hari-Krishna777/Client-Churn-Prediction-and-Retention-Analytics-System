import React, { useState, useEffect, useRef } from 'react';
import { batchApi } from '../api/batch';
import { BatchPredictResponse, BatchJobItem } from '../types';
import { Card } from '../components/common/Card';
import { Badge } from '../components/common/Badge';
import { LoadingSpinner } from '../components/common/LoadingSpinner';
import { useNotification } from '../context/NotificationContext';
import {
  UploadCloud,
  FileSpreadsheet,
  CheckCircle2,
  AlertTriangle,
  Download,
  Clock,
  Eye,
  Check,
  X,
  RefreshCw,
  ArrowRight,
} from 'lucide-react';

const EXPECTED_COLUMNS = [
  'customerID',
  'gender',
  'SeniorCitizen',
  'Partner',
  'Dependents',
  'tenure',
  'PhoneService',
  'MultipleLines',
  'InternetService',
  'OnlineSecurity',
  'OnlineBackup',
  'DeviceProtection',
  'TechSupport',
  'StreamingTV',
  'StreamingMovies',
  'Contract',
  'PaperlessBilling',
  'PaymentMethod',
  'MonthlyCharges',
  'TotalCharges',
];

export const UploadPage: React.FC = () => {
  const { notify } = useNotification();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [csvPreviewRows, setCsvPreviewRows] = useState<string[][]>([]);
  const [csvHeaders, setCsvHeaders] = useState<string[]>([]);
  const [uploading, setUploading] = useState(false);
  const [uploadResult, setUploadResult] = useState<BatchPredictResponse | null>(null);

  const [historyJobs, setHistoryJobs] = useState<BatchJobItem[]>([]);
  const [loadingHistory, setLoadingHistory] = useState(true);

  // Drag and drop state
  const [isDragging, setIsDragging] = useState(false);

  const fetchHistory = async () => {
    try {
      const jobs = await batchApi.listJobs();
      setHistoryJobs(jobs);
    } catch (err) {
      console.error('Failed to load batch history', err);
    } finally {
      setLoadingHistory(false);
    }
  };

  useEffect(() => {
    fetchHistory();
  }, []);

  const handleFileChange = (file: File) => {
    if (!file.name.toLowerCase().endsWith('.csv')) {
      notify('error', 'Please upload a valid CSV file (.csv extension).');
      return;
    }

    setSelectedFile(file);
    setUploadResult(null);

    // Read preview
    const reader = new FileReader();
    reader.onload = (e) => {
      const text = e.target?.result as string;
      if (!text) return;

      const lines = text.split(/\r\n|\n/).filter((l) => l.trim().length > 0);
      if (lines.length > 0) {
        const headers = lines[0].split(',').map((h) => h.trim().replace(/^"|"$/g, ''));
        setCsvHeaders(headers);

        const previewRows = lines.slice(1, 6).map((l) =>
          l.split(',').map((val) => val.trim().replace(/^"|"$/g, ''))
        );
        setCsvPreviewRows(previewRows);
      }
    };
    reader.readAsText(file);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFileChange(e.dataTransfer.files[0]);
    }
  };

  const handleUploadAndProcess = async () => {
    if (!selectedFile) return;

    setUploading(true);
    try {
      notify('info', `Validating and processing ${selectedFile.name}...`, 'Batch Engine Started');
      const res = await batchApi.uploadCsv(selectedFile);
      setUploadResult(res);
      notify(
        'success',
        `Processed ${res.total_predictions} customer records successfully!`,
        'Inference Completed'
      );
      fetchHistory();
    } catch (err: any) {
      notify('error', err.message || 'Batch prediction pipeline failed.', 'Processing Error');
    } finally {
      setUploading(false);
    }
  };

  // Check column mapping
  const mappedCount = EXPECTED_COLUMNS.filter((col) =>
    csvHeaders.some((h) => h.toLowerCase() === col.toLowerCase())
  ).length;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Dataset Upload & Batch Inference</h1>
        <p className="text-sm text-slate-500">
          Upload customer CSV files to trigger automated data validation, feature engineering, XGBoost inference, and SHAP-backed retention scoring.
        </p>
      </div>

      {/* Main Upload & Preview Area */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Upload Card */}
        <div className="lg:col-span-1 space-y-4">
          <Card title="Upload Customer CSV" icon={<UploadCloud className="w-4 h-4 text-indigo-600" />}>
            <div
              onDragOver={(e) => {
                e.preventDefault();
                setIsDragging(true);
              }}
              onDragLeave={() => setIsDragging(false)}
              onDrop={handleDrop}
              onClick={() => fileInputRef.current?.click()}
              className={`border-2 border-dashed rounded-xl p-6 text-center cursor-pointer transition ${
                isDragging
                  ? 'border-indigo-500 bg-indigo-50/50'
                  : 'border-slate-300 hover:border-indigo-400 hover:bg-slate-50/50'
              }`}
            >
              <input
                ref={fileInputRef}
                type="file"
                accept=".csv"
                onChange={(e) => e.target.files?.[0] && handleFileChange(e.target.files[0])}
                className="hidden"
              />

              <div className="w-12 h-12 mx-auto rounded-full bg-indigo-50 flex items-center justify-center text-indigo-600 mb-3">
                <FileSpreadsheet className="w-6 h-6" />
              </div>

              <div className="text-sm font-semibold text-slate-800">
                {selectedFile ? selectedFile.name : 'Choose a file or drag & drop'}
              </div>
              <p className="text-xs text-slate-500 mt-1">
                Accepts Telco formatted CSVs (up to 50MB)
              </p>

              {selectedFile && (
                <div className="mt-3 text-xs font-mono text-indigo-600 font-medium">
                  {(selectedFile.size / 1024).toFixed(1)} KB
                </div>
              )}
            </div>

            {selectedFile && (
              <div className="mt-4 space-y-3">
                <button
                  onClick={handleUploadAndProcess}
                  disabled={uploading}
                  className="w-full py-2.5 px-4 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white font-semibold text-sm shadow-sm transition flex items-center justify-center gap-2 disabled:opacity-50"
                >
                  {uploading ? (
                    <>
                      <LoadingSpinner size="sm" />
                      <span>Validating & Inferring...</span>
                    </>
                  ) : (
                    <>
                      <UploadCloud className="w-4 h-4" />
                      <span>Start Batch Inference</span>
                    </>
                  )}
                </button>
              </div>
            )}
          </Card>

          {/* Column Mapping Checker */}
          {csvHeaders.length > 0 && (
            <Card
              title="Column Mapping Status"
              subtitle={`${mappedCount} of ${EXPECTED_COLUMNS.length} expected fields detected`}
              icon={<Check className="w-4 h-4 text-emerald-600" />}
            >
              <div className="space-y-1.5 max-h-56 overflow-y-auto pr-1 text-xs">
                {EXPECTED_COLUMNS.map((col) => {
                  const isPresent = csvHeaders.some((h) => h.toLowerCase() === col.toLowerCase());
                  return (
                    <div
                      key={col}
                      className="flex items-center justify-between py-1 px-2 rounded bg-slate-50 border border-slate-100"
                    >
                      <span className="font-mono text-slate-700">{col}</span>
                      {isPresent ? (
                        <span className="flex items-center gap-1 text-[11px] font-medium text-emerald-600">
                          <Check className="w-3 h-3" /> Matched
                        </span>
                      ) : (
                        <span className="flex items-center gap-1 text-[11px] font-medium text-amber-600">
                          <AlertTriangle className="w-3 h-3" /> Imputed
                        </span>
                      )}
                    </div>
                  );
                })}
              </div>
            </Card>
          )}
        </div>

        {/* Preview & Results Area */}
        <div className="lg:col-span-2 space-y-4">
          {/* Latest Processing Result Alert */}
          {uploadResult && (
            <div className="bg-white rounded-xl border border-emerald-200 p-5 shadow-xs bg-gradient-to-br from-emerald-50/40 to-white">
              <div className="flex items-start justify-between">
                <div className="flex items-center space-x-3">
                  <div className="w-10 h-10 rounded-xl bg-emerald-100 text-emerald-700 flex items-center justify-center">
                    <CheckCircle2 className="w-5 h-5" />
                  </div>
                  <div>
                    <h3 className="text-base font-bold text-slate-900">
                      Batch Processing Completed: {uploadResult.filename}
                    </h3>
                    <p className="text-xs text-slate-500 font-mono">Job ID: {uploadResult.job_id}</p>
                  </div>
                </div>

                <a
                  href={`/api/batch/${uploadResult.job_id}/download`}
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-semibold shadow-xs transition"
                >
                  <Download className="w-3.5 h-3.5" />
                  Download Predictions CSV
                </a>
              </div>

              {/* Validation Summary Metrics */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mt-4">
                <div className="p-3 bg-white rounded-lg border border-slate-200">
                  <span className="text-[10px] text-slate-400 uppercase font-semibold">Total Records</span>
                  <div className="text-lg font-bold text-slate-800">
                    {uploadResult.validation_summary.total_records}
                  </div>
                </div>
                <div className="p-3 bg-white rounded-lg border border-slate-200">
                  <span className="text-[10px] text-emerald-600 uppercase font-semibold">Valid & Inferred</span>
                  <div className="text-lg font-bold text-emerald-600">
                    {uploadResult.validation_summary.valid_records}
                  </div>
                </div>
                <div className="p-3 bg-white rounded-lg border border-slate-200">
                  <span className="text-[10px] text-rose-600 uppercase font-semibold">Invalid Records</span>
                  <div className="text-lg font-bold text-rose-600">
                    {uploadResult.validation_summary.invalid_records}
                  </div>
                </div>
                <div className="p-3 bg-white rounded-lg border border-slate-200">
                  <span className="text-[10px] text-amber-600 uppercase font-semibold">Duplicates Skipped</span>
                  <div className="text-lg font-bold text-amber-600">
                    {uploadResult.validation_summary.duplicate_records}
                  </div>
                </div>
              </div>

              {/* Risk Distribution Breakdown */}
              <div className="mt-4 pt-4 border-t border-slate-100 flex items-center justify-between">
                <span className="text-xs text-slate-500 font-medium">Batch Risk Categorization:</span>
                <div className="flex items-center gap-2">
                  <span className="text-xs px-2 py-0.5 rounded-md bg-emerald-100 text-emerald-800 font-medium">
                    Low: {uploadResult.risk_distribution.LOW}
                  </span>
                  <span className="text-xs px-2 py-0.5 rounded-md bg-amber-100 text-amber-800 font-medium">
                    Medium: {uploadResult.risk_distribution.MEDIUM}
                  </span>
                  <span className="text-xs px-2 py-0.5 rounded-md bg-rose-100 text-rose-800 font-medium">
                    High: {uploadResult.risk_distribution.HIGH}
                  </span>
                </div>
              </div>
            </div>
          )}

          {/* File Preview Table */}
          {csvHeaders.length > 0 && (
            <Card
              title="CSV Data Preview"
              subtitle="Showing first 5 records of uploaded dataset"
              icon={<Eye className="w-4 h-4 text-indigo-600" />}
            >
              <div className="overflow-x-auto max-h-72">
                <table className="w-full text-xs text-left">
                  <thead className="bg-slate-100 text-slate-700 font-semibold sticky top-0">
                    <tr>
                      {csvHeaders.slice(0, 8).map((h, i) => (
                        <th key={i} className="px-3 py-2 border-b border-slate-200 font-mono">
                          {h}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {csvPreviewRows.map((row, rIdx) => (
                      <tr key={rIdx} className="hover:bg-slate-50">
                        {row.slice(0, 8).map((cell, cIdx) => (
                          <td key={cIdx} className="px-3 py-2 text-slate-600 whitespace-nowrap">
                            {cell}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Card>
          )}

          {/* Batch Processing History */}
          <Card
            title="Upload & Processing History"
            subtitle="Previous batch prediction runs, execution metrics, and generated reports"
            icon={<Clock className="w-4 h-4 text-slate-600" />}
            action={
              <button
                onClick={fetchHistory}
                className="text-xs text-indigo-600 hover:text-indigo-800 flex items-center gap-1"
              >
                <RefreshCw className="w-3.5 h-3.5" /> Refresh
              </button>
            }
          >
            {loadingHistory ? (
              <LoadingSpinner size="md" label="Loading batch history..." />
            ) : historyJobs.length === 0 ? (
              <div className="text-center py-8 text-sm text-slate-400">
                No previous batch jobs found. Upload a CSV to get started.
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-xs text-left">
                  <thead className="bg-slate-50 text-slate-500 font-semibold uppercase tracking-wider text-[11px]">
                    <tr>
                      <th className="px-3 py-2.5">File Name</th>
                      <th className="px-3 py-2.5">Status</th>
                      <th className="px-3 py-2.5">Total Records</th>
                      <th className="px-3 py-2.5">Processed</th>
                      <th className="px-3 py-2.5">Timestamp</th>
                      <th className="px-3 py-2.5 text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {historyJobs.map((job) => (
                      <tr key={job.job_id} className="hover:bg-slate-50/80 transition">
                        <td className="px-3 py-2.5 font-medium text-slate-800 flex items-center gap-2">
                          <FileSpreadsheet className="w-4 h-4 text-slate-400" />
                          <span className="truncate max-w-xs">{job.filename}</span>
                        </td>
                        <td className="px-3 py-2.5">
                          <span
                            className={`px-2 py-0.5 rounded-full text-[10px] font-semibold border ${
                              job.status === 'COMPLETED'
                                ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                                : job.status === 'FAILED'
                                ? 'bg-rose-50 text-rose-700 border-rose-200'
                                : 'bg-amber-50 text-amber-700 border-amber-200 animate-pulse'
                            }`}
                          >
                            {job.status}
                          </span>
                        </td>
                        <td className="px-3 py-2.5 text-slate-600">{job.total_records}</td>
                        <td className="px-3 py-2.5 text-emerald-600 font-semibold">
                          {job.successfully_processed}
                        </td>
                        <td className="px-3 py-2.5 text-slate-400">
                          {job.created_at ? new Date(job.created_at).toLocaleString() : 'N/A'}
                        </td>
                        <td className="px-3 py-2.5 text-right">
                          <a
                            href={`/api/batch/${job.job_id}/download`}
                            target="_blank"
                            rel="noreferrer"
                            className="inline-flex items-center gap-1 px-2.5 py-1 rounded bg-slate-100 hover:bg-slate-200 text-slate-700 font-medium transition"
                          >
                            <Download className="w-3 h-3" />
                            CSV
                          </a>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </Card>
        </div>
      </div>
    </div>
  );
};
