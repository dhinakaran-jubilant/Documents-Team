/**
 * Project: Fin Report - Documents team
 * Author: Dhinakaran Sekar
 * Email: dhinakaran.s@jubilantenterprises.in
 * Date: 2026-04-30 18:41
 * Description: Upload component for selecting Excel files, processing them via the backend, and downloading generated PDF reports.
 */

import Layout from './Layout';
import React, { useState, useRef } from 'react';
import axios from 'axios';
import { DotLottiePlayer } from '@dotlottie/react-player';
import config from './config';

/**
 * Upload component.
 * @param {Object} props - Component props.
 * @param {Object} props.user - Current authenticated user object.
 * @param {Function} props.onLogout - Callback function for user logout.
 */
function Upload({ user, onLogout }) {
  const [file, setFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState(null);
  const [dragActive, setDragActive] = useState(false);
  const [showSuccessModal, setShowSuccessModal] = useState(false);
  const [successMessage, setSuccessMessage] = useState('');
  
  const inputRef = useRef(null);

  /**
   * Handles drag events for the file upload area.
   */
  const handleDrag = function (e) {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  /**
   * Handles file drop events.
   */
  const handleDrop = function (e) {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const droppedFile = e.dataTransfer.files[0];
      if (isValidExcel(droppedFile)) {
        setFile(droppedFile);
        setStatus(null);
      } else {
        setStatus({ type: 'error', message: 'Please upload a valid Excel file (.xlsx, .xls)' });
      }
    }
  };

  /**
   * Handles file input change events.
   */
  const handleChange = function (e) {
    e.preventDefault();
    if (e.target.files && e.target.files[0]) {
      const selectedFile = e.target.files[0];
      if (isValidExcel(selectedFile)) {
        setFile(selectedFile);
        setStatus(null);
      } else {
        setStatus({ type: 'error', message: 'Please upload a valid Excel file (.xlsx, .xls)' });
      }
    }
  };

  /**
   * Validates if a file is a valid Excel format.
   */
  const isValidExcel = (f) => {
    return f.name.endsWith('.xlsx') || f.name.endsWith('.xls') ||
      ["application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "application/vnd.ms-excel"].includes(f.type);
  };

  /**
   * Triggers the file input click.
   */
  const onButtonClick = () => {
    inputRef.current.click();
  };

  /**
   * Clears the selected file.
   */
  const removeFile = (e) => {
    if (e && typeof e !== 'number') e.stopPropagation();
    setFile(null);
    setStatus(null);
    if (inputRef.current) inputRef.current.value = '';
  };

  /**
   * Sends the selected file to the backend for processing.
   * Downloads the resulting ZIP file on success.
   */
  const handleSubmit = async () => {
    if (!file) return;

    setLoading(true);
    setStatus(null);

    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await axios.post(`${config.API_BASE_URL}/upload`, formData, {
        responseType: 'blob',
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });

      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', 'financial_reports.zip');
      document.body.appendChild(link);
      link.click();
      
      link.parentNode.removeChild(link);
      window.URL.revokeObjectURL(url);
      
      setSuccessMessage('Reports generated and downloaded successfully!');
      setShowSuccessModal(true);
      setFile(null);
      if (inputRef.current) inputRef.current.value = '';
    } catch (err) {
      console.error(err);
      let errorMsg = 'Failed to process file. Ensure backend is running.';

      if (err.response && err.response.data && err.response.data.type === 'application/json') {
        try {
          const text = await new Response(err.response.data).text();
          const json = JSON.parse(text);
          if (json.error) {
            errorMsg = json.error;
          }
        } catch (e) { }
      }

      setStatus({ type: 'error', message: errorMsg });
    } finally {
      setLoading(false);
    }
  };

  const fileInputRef = inputRef;
  const isProcessing = loading;
  const errorMessage = status?.type === 'error' ? status.message : null;
  const selectedFiles = file ? [file] : [];

  const handleUploadClick = onButtonClick;
  const handleDragOver = handleDrag;
  const handleFileChange = handleChange;
  const handleProcessFiles = handleSubmit;
  const dismissError = () => setStatus(null);

  return (
    <Layout user={user} onLogout={onLogout} activeTab="fin-report" breadcrumbs={['Fin Report']}>
        <main className="flex-1 bg-slate-50 dark:bg-[#101822] px-10 pb-8 transition-colors duration-300">
                <div className="flex flex-col gap-10">
                    {/* Header Section */}
                    <div className="flex flex-col items-start text-left gap-2">
                        <h1 className="text-4xl font-black tracking-tight text-slate-900 dark:text-white transition-colors duration-300">Fin Report</h1>
                        <p className="text-slate-600 dark:text-slate-400 text-sm leading-relaxed transition-colors duration-300">Upload Excel files containing financial collection and dues data. The system automatically processes the records to generate structured PDF reports grouped by Branch, Consultant, and Collection Executive, complete with dedicated TDS listings and total amount calculations.</p>
                    </div>

                    {/* Main Upload Card */}
                    <div className="bg-white dark:bg-[#0f172b] rounded-3xl shadow-2xl border border-slate-200 dark:border-slate-800 overflow-hidden transition-colors duration-300">
                        <div className="p-8">
                            <div
                                className={`flex flex-col items-center justify-center gap-8 rounded-2xl border-2 border-dashed transition-all duration-300 p-5 cursor-pointer group ${dragActive ? 'border-blue-500 bg-blue-50 dark:bg-[#1a2846]' : 'border-slate-300 dark:border-slate-800 bg-slate-50 dark:bg-[#16223b] hover:border-slate-400 dark:hover:border-slate-700 hover:bg-slate-100 dark:hover:bg-[#1a2846]'}`}
                                onClick={handleUploadClick}
                                onDragEnter={handleDrag}
                                onDragLeave={handleDrag}
                                onDragOver={handleDragOver}
                                onDrop={handleDrop}
                            >
                                <input
                                    type="file"
                                    ref={fileInputRef}
                                    className="hidden"
                                    accept=".xlsx, .xls"
                                    onChange={handleFileChange}
                                />
                                <div className="flex flex-col items-center gap-5">
                                    <div className="w-15 h-15 bg-white dark:bg-[#111926] border border-slate-200 dark:border-slate-800 rounded-full flex items-center justify-center shadow-xl group-hover:scale-110 transition-transform">
                                        <span className="material-symbols-outlined text-5xl text-blue-500">upload_file</span>
                                    </div>
                                    <div className="text-center">
                                        <h4 className="text-2xl font-bold text-slate-900 dark:text-white mb-2 transition-colors duration-300">Drag and drop files here</h4>
                                        <p className="text-slate-500 text-sm">Supports .XLSX Excel files only.</p>
                                    </div>
                                </div>
                                <button className="flex items-center gap-3 px-10 py-4 bg-blue-600 text-white rounded-xl font-bold shadow-xl shadow-blue-600/20 hover:bg-blue-700 transition-all active:scale-95 cursor-pointer">
                                    <span className="material-symbols-outlined text-xl">add_circle</span>
                                    Browse Files
                                </button>
                            </div>

                            {/* Inline Error Message */}
                            {errorMessage && (
                                <div className="mt-6 bg-red-500/10 border border-red-500/20 text-red-500 px-6 py-4 rounded-xl flex items-center gap-4 animate-in fade-in slide-in-from-top-2">
                                    <span className="material-symbols-outlined text-2xl">error_outline</span>
                                    <span className="text-[12px] font-bold flex-1 tracking-widest">{errorMessage}</span>
                                    <button
                                        onClick={dismissError}
                                        className="flex items-center justify-center h-8 w-8 rounded-lg hover:bg-red-500/20 transition-colors"
                                    >
                                        <span className="material-symbols-outlined text-xl">close</span>
                                    </button>
                                </div>
                            )}

                            {/* Selected Files List */}
                            {selectedFiles.length > 0 && (
                                <div className="mt-10 flex flex-col gap-4">
                                    <h5 className="font-black text-[11px] uppercase tracking-[0.2em] text-slate-500 ml-1">Selected File:</h5>
                                    {selectedFiles.map((f, index) => (
                                        <div key={index} className="flex items-center justify-between p-5 rounded-2xl border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-[#111926]/50 transition-colors duration-300 animate-in zoom-in-95 duration-300">
                                            <div className="flex items-center gap-4 overflow-hidden">
                                                <div className="w-10 h-10 bg-blue-50 dark:bg-blue-600/10 rounded-lg flex items-center justify-center">
                                                    <span className="material-symbols-outlined text-blue-500">description</span>
                                                </div>
                                                <div className="flex flex-col">
                                                    <span className="text-sm font-bold text-slate-900 dark:text-white truncate transition-colors duration-300">{f.name}</span>
                                                    <span className="text-[10px] font-black uppercase tracking-widest text-slate-500">
                                                        {(f.size / 1024 / 1024).toFixed(2)} MB
                                                    </span>
                                                </div>
                                            </div>
                                            <button
                                                onClick={() => removeFile()}
                                                className="flex items-center justify-center rounded-xl h-10 w-10 text-slate-400 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-500/10 transition-all cursor-pointer"
                                            >
                                                <span className="material-symbols-outlined">delete</span>
                                            </button>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>
                    </div>

                    {/* Action Buttons */}
                    <div className="flex justify-end gap-5 mt-4">
                        <button
                            onClick={() => removeFile()}
                            className="flex items-center gap-3 px-8 py-3.5 rounded-xl border border-slate-300 dark:border-slate-800 text-slate-600 dark:text-slate-500 font-bold uppercase tracking-widest text-[11px] hover:text-slate-900 dark:hover:text-white hover:bg-slate-200 dark:hover:bg-slate-800 transition-all cursor-pointer"
                        >
                            <span className="material-symbols-outlined text-xl">restart_alt</span>
                            Clear All
                        </button>
                        <button
                            onClick={handleProcessFiles}
                            disabled={!file || isProcessing}
                            className={`flex items-center gap-3 px-10 py-3.5 bg-blue-600 text-white rounded-xl font-bold shadow-2xl shadow-blue-600/20 transition-all ${isProcessing ? 'opacity-70 cursor-not-allowed' : 'hover:bg-blue-700 active:scale-95 cursor-pointer'}`}
                        >
                            {isProcessing ? (
                                <>
                                    <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                                    <span className="text-[11px] font-black uppercase tracking-[0.2em]">Processing...</span>
                                </>
                            ) : (
                                <>
                                    <span className="material-symbols-outlined text-xl">play_circle</span>
                                    <span className="text-[11px] font-black uppercase tracking-[0.2em]">Process</span>
                                </>
                            )}
                        </button>
                    </div>
                </div>

                {/* Footer */}
                <footer className="mt-15 pt-6 border-t border-slate-200 dark:border-slate-800/50 text-center text-[12px] font-bold tracking-[0.1em] text-slate-500">
                    <p>
                        All rights reserved &copy; 2026 @ Jubilant Capital. Designed and Developed by{' '}
                        <a href="mailto:dhinakaran.s@jubilantenterprises.in" className="text-blue-500 hover:underline">
                            Dhinakaran Sekar
                        </a>
                    </p>
                </footer>
            </main>

            {/* Processing Modal Overlay */}
            {isProcessing && (
                <div className="fixed inset-0 z-[100] flex items-center justify-center bg-slate-900/40 dark:bg-slate-900/60 backdrop-blur-sm animate-in fade-in duration-300">
                    <div className="bg-white dark:bg-[#0a0f18] rounded-3xl shadow-2xl p-12 flex flex-col items-center gap-8 max-w-sm w-full mx-4 border border-slate-200 dark:border-slate-800 animate-in zoom-in-95 duration-300">
                        <div className="size-32">
                            <DotLottiePlayer
                                src="https://lottie.host/26c29f4c-00d1-4c13-a161-b608499b7ccb/5uUeWZYlLT.lottie"
                                autoplay
                                loop
                                className="size-full"
                            />
                        </div>
                        <div className="text-center">
                            <h3 className="text-2xl font-black tracking-tight text-slate-900 dark:text-white mb-2 transition-colors duration-300">Processing Files</h3>
                            <p className="text-slate-600 dark:text-slate-400 text-sm transition-colors duration-300">Please wait, this may take a few moments...</p>
                        </div>
                    </div>
                </div>
            )}

            {/* Success Modal Overlay */}
            {showSuccessModal && (
                <div className="fixed inset-0 z-[110] flex items-center justify-center bg-slate-900/40 dark:bg-black/60 backdrop-blur-sm p-4 animate-in fade-in duration-200">
                    <div className="bg-white dark:bg-[#0a0f18] rounded-3xl shadow-2xl p-12 flex flex-col items-center max-w-sm w-full mx-4 border border-slate-200 dark:border-slate-800 animate-in zoom-in-95 duration-200 text-center">
                        <div className="w-15 h-15 rounded-full bg-emerald-50 dark:bg-emerald-600/10 text-emerald-500 flex items-center justify-center mb-8 border border-emerald-200 dark:border-emerald-500/20">
                            <span className="material-symbols-outlined text-[40px]">check_circle</span>
                        </div>
                        <h3 className="text-2xl font-black tracking-tight text-slate-900 dark:text-white mb-2 transition-colors duration-300">Process Complete!</h3>
                        <p className="text-slate-600 dark:text-slate-400 text-sm mb-10 leading-relaxed transition-colors duration-300">
                            {successMessage || 'Your reports have been generated and downloaded successfully.'}
                        </p>
                        <button
                            onClick={() => setShowSuccessModal(false)}
                            className="w-full py-4 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl font-bold uppercase tracking-widest text-[11px] transition-all cursor-pointer shadow-xl shadow-emerald-600/20"
                        >
                            Close
                        </button>
                    </div>
                </div>
            )}
    </Layout>
  );
}

export default Upload;
