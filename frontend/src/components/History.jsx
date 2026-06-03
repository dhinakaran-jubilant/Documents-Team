/**
 * Project: Fin Report - Documents team
 * Author: Dhinakaran Sekar
 * Email: dhinakaran.s@jubilantenterprises.in
 * Date: 2026-06-02
 * Description: History component for displaying and managing document generation history logs.
 */

import React, { useState, useEffect } from 'react';
import Layout from './Layout';
import config from './config';
import axios from 'axios';

const cleanDisplayLenderName = (name) => {
    if (!name) return '';
    return name.replace(/^(M\/S|M\/R|MRS|MR)(?:\.|\s)\s*/i, '').trim();
};

const LENDER_COLORS = [
    { bg: 'bg-blue-50 dark:bg-blue-950/30', text: 'text-blue-700 dark:text-blue-300', border: 'border-blue-200/50 dark:border-blue-800/30' },
    { bg: 'bg-indigo-50 dark:bg-indigo-950/30', text: 'text-indigo-700 dark:text-indigo-300', border: 'border-indigo-200/50 dark:border-indigo-800/30' },
    { bg: 'bg-purple-50 dark:bg-purple-950/30', text: 'text-purple-700 dark:text-purple-300', border: 'border-purple-200/50 dark:border-purple-800/30' },
    { bg: 'bg-violet-50 dark:bg-violet-950/30', text: 'text-violet-700 dark:text-violet-300', border: 'border-violet-200/50 dark:border-violet-800/30' },
    { bg: 'bg-pink-50 dark:bg-pink-950/30', text: 'text-pink-700 dark:text-pink-300', border: 'border-pink-200/50 dark:border-pink-800/30' },
    { bg: 'bg-emerald-50 dark:bg-emerald-950/30', text: 'text-emerald-700 dark:text-emerald-300', border: 'border-emerald-200/50 dark:border-emerald-800/30' },
    { bg: 'bg-teal-50 dark:bg-teal-950/30', text: 'text-teal-700 dark:text-teal-300', border: 'border-teal-200/50 dark:border-teal-800/30' },
    { bg: 'bg-cyan-50 dark:bg-cyan-950/30', text: 'text-cyan-700 dark:text-cyan-300', border: 'border-cyan-200/50 dark:border-cyan-800/30' },
    { bg: 'bg-sky-50 dark:bg-sky-950/30', text: 'text-sky-700 dark:text-sky-300', border: 'border-sky-200/50 dark:border-sky-800/30' },
    { bg: 'bg-amber-50 dark:bg-amber-950/30', text: 'text-amber-700 dark:text-amber-300', border: 'border-amber-200/50 dark:border-amber-800/30' }
];

const getLenderColor = (name) => {
    if (!name) return LENDER_COLORS[0];
    const cleanName = cleanDisplayLenderName(name).toUpperCase();
    let hash = 0;
    for (let i = 0; i < cleanName.length; i++) {
        hash = cleanName.charCodeAt(i) + ((hash << 5) - hash);
    }
    const index = Math.abs(hash) % LENDER_COLORS.length;
    return LENDER_COLORS[index];
};

const formatDate = (dateStr) => {
    if (!dateStr) return '';
    const match = dateStr.match(/^(\d{4})-(\d{2})-(\d{2})\s+(\d{2}):(\d{2}):(\d{2})$/);
    if (!match) {
        try {
            const dateObj = new Date(dateStr);
            if (isNaN(dateObj.getTime())) return dateStr;
            const day = String(dateObj.getDate()).padStart(2, '0');
            const month = String(dateObj.getMonth() + 1).padStart(2, '0');
            const year = dateObj.getFullYear();
            let hours = dateObj.getHours();
            const minutes = String(dateObj.getMinutes()).padStart(2, '0');
            const ampm = hours >= 12 ? 'pm' : 'am';
            hours = hours % 12;
            hours = hours ? hours : 12;
            const formattedHours = String(hours).padStart(2, '0');
            return `${day}-${month}-${year} ${formattedHours}:${minutes} ${ampm}`;
        } catch (e) {
            return dateStr;
        }
    }
    const [_, year, month, day, hoursStr, minutes] = match;
    let hours = parseInt(hoursStr, 10);
    const ampm = hours >= 12 ? 'pm' : 'am';
    hours = hours % 12;
    hours = hours ? hours : 12;
    const formattedHours = String(hours).padStart(2, '0');
    return `${day}-${month}-${year} ${formattedHours}:${minutes} ${ampm}`;
};

function History({ user, onLogout, onTabChange }) {
    const [historyList, setHistoryList] = useState([]);
    const [loading, setLoading] = useState(true);
    const [searchTerm, setSearchTerm] = useState('');
    const [currentPage, setCurrentPage] = useState(1);
    const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
    const [deleteId, setDeleteId] = useState(null);
    const [actionLoading, setActionLoading] = useState(false);
    const [notification, setNotification] = useState(null);
    const [selectedHistoryItem, setSelectedHistoryItem] = useState(null);

    const ITEMS_PER_PAGE = 20;

    // Check if user has access to documat
    const hasDocumatAccess = user?.role === 'admin' || !user?.accessed_menus || user.accessed_menus.includes('documat');

    useEffect(() => {
        if (hasDocumatAccess) {
            fetchHistory();
        }
    }, [hasDocumatAccess]);

    const fetchHistory = async () => {
        setLoading(true);
        try {
            const response = await axios.get(`${config.API_BASE_URL}/api/documat/history/`);
            if (response.data?.success) {
                setHistoryList(response.data.history || []);
            } else {
                showToast(response.data?.message || 'Failed to fetch history', 'error');
            }
        } catch (error) {
            console.error('Error fetching history:', error);
            showToast(error.response?.data?.message || 'Error connecting to server', 'error');
        } finally {
            setLoading(false);
        }
    };

    const showToast = (message, type = 'success') => {
        setNotification({ message, type });
        setTimeout(() => {
            setNotification(null);
        }, 4000);
    };

    const handleDeleteClick = (id) => {
        setDeleteId(id);
        setShowDeleteConfirm(true);
    };

    const confirmDelete = async () => {
        if (!deleteId) return;
        setActionLoading(true);
        try {
            const response = await axios.delete(`${config.API_BASE_URL}/api/documat/history/${deleteId}`);
            if (response.data?.success) {
                showToast('History log deleted successfully', 'success');
                setHistoryList(prev => prev.filter(item => item.id !== deleteId));
            } else {
                showToast(response.data?.message || 'Failed to delete record', 'error');
            }
        } catch (error) {
            console.error('Error deleting history:', error);
            showToast(error.response?.data?.message || 'Error connecting to server', 'error');
        } finally {
            setActionLoading(false);
            setShowDeleteConfirm(false);
            setDeleteId(null);
        }
    };

    // Filter history based on search term
    const filteredHistory = historyList.filter(item => {
        const query = searchTerm.toLowerCase().trim();
        if (!query) return true;
        const cleanedLenders = (item.lenders || '')
            .split(',')
            .map(l => cleanDisplayLenderName(l.trim()))
            .join(', ');
        return (
            (item.proprietor_name || '').toLowerCase().includes(query) ||
            (item.lenders || '').toLowerCase().includes(query) ||
            cleanedLenders.toLowerCase().includes(query) ||
            (item.username || '').toLowerCase().includes(query)
        );
    });

    // Pagination slicing
    const totalPages = Math.ceil(filteredHistory.length / ITEMS_PER_PAGE) || 1;
    const pagedHistory = filteredHistory.slice((currentPage - 1) * ITEMS_PER_PAGE, currentPage * ITEMS_PER_PAGE);
    // Reset pagination to first page if search term changes
    useEffect(() => {
        setCurrentPage(1);
    }, [searchTerm]);

    const startRecord = filteredHistory.length > 0 ? (currentPage - 1) * ITEMS_PER_PAGE + 1 : 0;
    const endRecord = Math.min(currentPage * ITEMS_PER_PAGE, filteredHistory.length);

    return (
        <Layout user={user} onLogout={onLogout} onTabChange={onTabChange} activeTab="history">
            <main className="flex-1 flex flex-col bg-slate-50 dark:bg-[#101822] px-10 pt-10 pb-8 transition-colors duration-300 h-full overflow-hidden relative">
                {/* Custom Toast Alert */}
                {notification && (
                    <div className={`fixed top-6 right-6 z-[200] flex items-center gap-3 px-6 py-4 rounded-2xl shadow-xl border animate-in slide-in-from-top-4 duration-300 ${
                        notification.type === 'error'
                            ? 'bg-red-50 dark:bg-red-950/20 border-red-200 dark:border-red-800 text-red-800 dark:text-red-300'
                            : 'bg-green-50 dark:bg-green-950/20 border-green-200 dark:border-green-800 text-green-800 dark:text-green-300'
                    }`}>
                        <span className="material-symbols-outlined text-lg">
                            {notification.type === 'error' ? 'error' : 'check_circle'}
                        </span>
                        <p className="text-[13px] font-bold tracking-tight">{notification.message}</p>
                    </div>
                )}

                <div className="flex-1 flex flex-col min-h-0">
                    {/* Header Section */}
                    <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-6 shrink-0">
                        <div className="flex flex-col items-start text-left gap-2 max-w-3xl">
                            <h1 className="text-4xl font-black tracking-tight text-slate-900 dark:text-white transition-colors duration-300">History</h1>
                        </div>
                        {hasDocumatAccess && (
                            <div className="relative w-full md:w-80 self-start md:self-center">
                                <span className="material-symbols-outlined absolute left-5 top-1/2 -translate-y-1/2 text-slate-400">
                                    search
                                </span>
                                <input
                                    type="text"
                                    placeholder="Search by proprietor, lender..."
                                    value={searchTerm}
                                    onChange={(e) => setSearchTerm(e.target.value)}
                                    className="w-full pl-12 pr-6 py-3 rounded-2xl bg-slate-100/70 focus:bg-white dark:bg-slate-900/40 dark:focus:bg-[#101726] border border-slate-200 dark:border-slate-800 text-slate-900 dark:text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all text-[13px] font-semibold"
                                />
                            </div>
                        )}
                    </div>

                    {/* History Data Card */}
                    <div className="flex-1 flex flex-col min-h-0 bg-white dark:bg-[#0f172b] rounded-3xl shadow-2xl border border-slate-200 dark:border-slate-800 overflow-hidden transition-colors duration-300">
                        
                        {/* Access Denied State */}
                        {!hasDocumatAccess ? (
                            <div className="flex-1 flex flex-col items-center justify-center text-center p-10">
                                <div className="w-20 h-20 rounded-full bg-amber-100 dark:bg-amber-600/10 text-amber-500 flex items-center justify-center mb-6 border border-amber-200 dark:border-amber-500/20">
                                    <span className="material-symbols-outlined text-[40px]">lock_person</span>
                                </div>
                                <h3 className="text-xl font-black text-slate-900 dark:text-white tracking-tight mb-2">Access Restrained</h3>
                                <p className="text-slate-500 dark:text-slate-400 text-sm max-w-md leading-relaxed">
                                    Document generation history is exclusively reserved for **Documat** authorized personnel. If you believe this is an error, please contact your System Administrator.
                                </p>
                            </div>
                        ) : (
                            <>
                                {loading && historyList.length === 0 ? (
                                    <div className="flex flex-col items-center justify-center py-20 gap-4">
                                        <div className="w-10 h-10 border-4 border-blue-600/30 border-t-blue-600 rounded-full animate-spin" />
                                        <span className="text-[11px] font-black uppercase tracking-[0.2em] text-slate-400">Loading History Logs...</span>
                                    </div>
                                ) : filteredHistory.length === 0 ? (
                                    <div className="flex flex-col items-center justify-center py-20 gap-4 text-center">
                                        <div className="w-16 h-16 rounded-full bg-slate-100 dark:bg-slate-800 flex items-center justify-center text-slate-400">
                                            <span className="material-symbols-outlined text-4xl">folder_open</span>
                                        </div>
                                        <div>
                                            <h4 className="text-xl font-bold text-slate-900 dark:text-white mb-1">No logs found</h4>
                                            <p className="text-slate-500 text-sm">
                                                {searchTerm ? "No generation records match your filter search parameters." : "Generate document packages inside the Documat menu to see history logs."}
                                            </p>
                                        </div>
                                    </div>
                                ) : (
                                    <>
                                        {/* Fixed column header */}
                                        <div className="shrink-0 bg-slate-50/90 dark:bg-slate-900/40 border-b border-slate-200 dark:border-slate-800/80">
                                            <table className="w-full border-collapse text-left table-fixed">
                                                <colgroup>
                                                    <col style={{width:'8%'}} />
                                                    <col style={{width:'12%'}} />
                                                    <col style={{width:'22%'}} />
                                                    <col style={{width:'18%'}} />
                                                    <col style={{width:'12%'}} />
                                                    <col style={{width:'12%'}} />
                                                </colgroup>
                                                <thead>
                                                    <tr className="text-slate-500 dark:text-slate-400 text-[11px] font-black uppercase tracking-[0.2em]">
                                                        <th className="py-6 px-6 text-center">S.No</th>
                                                        <th className="py-6 px-6">Username</th>
                                                        <th className="py-6 px-8">Borrower</th>
                                                        <th className="py-6 px-6">Lender</th>
                                                        <th className="py-6 px-6 text-right">Loan Amount</th>
                                                        <th className="py-6 px-6">Created On</th>
                                                    </tr>
                                                </thead>
                                            </table>
                                        </div>

                                        {/* Scrollable body container */}
                                        <div className="flex-1 overflow-x-auto overflow-y-auto scrollbar-slim">
                                            <table className="w-full border-collapse text-left table-fixed">
                                                <colgroup>
                                                    <col style={{width:'8%'}} />
                                                    <col style={{width:'12%'}} />
                                                    <col style={{width:'22%'}} />
                                                    <col style={{width:'18%'}} />
                                                    <col style={{width:'12%'}} />
                                                    <col style={{width:'12%'}} />
                                                </colgroup>
                                                <tbody className="divide-y divide-slate-100 dark:divide-slate-800/60">
                                                    {pagedHistory.map((item, index) => {
                                                        const serialNumber = (currentPage - 1) * ITEMS_PER_PAGE + index + 1;
                                                        return (
                                                            <tr
                                                                key={item.id}
                                                                onClick={() => setSelectedHistoryItem(item)}
                                                                className="hover:bg-slate-50/55 dark:hover:bg-slate-800/20 transition-colors duration-200 cursor-pointer"
                                                            >
                                                                {/* S.No */}
                                                                <td className="py-3 px-6 text-center text-[13px] font-semibold text-slate-500 dark:text-slate-400">
                                                                    {serialNumber}
                                                                </td>

                                                                {/* Generated By */}
                                                                <td className="py-3 px-6">
                                                                    <div className="flex items-center gap-2 min-w-0">
                                                                        <span className="text-[14px] font-semibold text-slate-700 dark:text-slate-300 truncate" title={item.username}>{item.username}</span>
                                                                    </div>
                                                                </td>

                                                                {/* Proprietor Name */}
                                                                <td className="py-3 px-8">
                                                                    <div className="flex flex-col min-w-0">
                                                                        <span className="text-[14px] font-black text-slate-900 dark:text-white tracking-tight truncate">{item.proprietor_name}</span>
                                                                        <span className="text-[10px] text-slate-400 dark:text-slate-500 font-bold uppercase tracking-wider mt-0.5">{item.entity_type || 'Proprietor'}</span>
                                                                    </div>
                                                                </td>

                                                                {/* Lenders */}
                                                                <td className="py-3 px-6">
                                                                    <div className="flex flex-wrap gap-1.5 max-h-[60px] overflow-y-auto scrollbar-slim">
                                                                        {(item.lenders || '').split(',').map((lender, lIdx) => {
                                                                            const trimmedLender = lender.trim();
                                                                            const colors = getLenderColor(trimmedLender);
                                                                            return (
                                                                                <span
                                                                                    key={lIdx}
                                                                                    className={`inline-flex items-center px-2.5 py-1 rounded-lg text-[10px] font-bold ${colors.bg} ${colors.text} border ${colors.border} truncate max-w-[200px]`}
                                                                                    title={trimmedLender}
                                                                                >
                                                                                    {cleanDisplayLenderName(trimmedLender)}
                                                                                </span>
                                                                            );
                                                                        })}
                                                                    </div>
                                                                </td>

                                                                {/* Total Loan Amount */}
                                                                <td className="py-3 px-6 text-right font-mono text-[13px] font-black text-emerald-600 dark:text-emerald-400">
                                                                    ₹ {item.total_loan_amount}
                                                                </td>

                                                                {/* Date & Time */}
                                                                <td className="py-3 px-6 text-center text-[11px] font-semibold text-slate-500 dark:text-slate-400">
                                                                    <div className="flex items-center justify-center gap-1.5">
                                                                        <span>{formatDate(item.generated_at)}</span>
                                                                    </div>
                                                                </td>
                                                            </tr>
                                                        );
                                                    })}
                                                </tbody>
                                            </table>
                                        </div>

                                        {/* Pagination Footer */}
                                        <div className="shrink-0 flex flex-col sm:flex-row items-center justify-between gap-4 px-8 py-5 border-t border-slate-200 dark:border-slate-800/80 bg-slate-50/50 dark:bg-slate-900/10 transition-colors duration-300">
                                            <div className="text-[11px] font-black uppercase tracking-[0.2em] text-slate-400 dark:text-slate-500">
                                                Showing <span className="text-slate-950 dark:text-white font-bold">{startRecord}</span> to <span className="text-slate-950 dark:text-white font-bold">{endRecord}</span> of <span className="text-slate-950 dark:text-white font-bold">{filteredHistory.length}</span> records
                                            </div>
                                            <div className="flex items-center gap-2">
                                                <button
                                                    type="button"
                                                    onClick={() => setCurrentPage(prev => Math.max(1, prev - 1))}
                                                    disabled={currentPage === 1}
                                                    className="h-9 px-4 rounded-xl border border-slate-200 dark:border-slate-800/80 text-slate-600 dark:text-slate-400 hover:text-slate-950 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-slate-800 disabled:opacity-40 disabled:cursor-not-allowed disabled:hover:bg-transparent transition-all flex items-center justify-center gap-1 cursor-pointer font-bold text-[11px] uppercase tracking-widest"
                                                >
                                                    <span className="material-symbols-outlined text-base">chevron_left</span>
                                                    Prev
                                                </button>
                                                
                                                <div className="flex items-center gap-1.5">
                                                    {Array.from({ length: totalPages }, (_, i) => i + 1).map((p) => (
                                                        <button
                                                            key={p}
                                                            type="button"
                                                            onClick={() => setCurrentPage(p)}
                                                            className={`h-9 w-9 rounded-xl flex items-center justify-center font-bold text-xs transition-all cursor-pointer ${
                                                                currentPage === p
                                                                    ? 'bg-blue-600 text-white shadow-md shadow-blue-600/20'
                                                                    : 'text-slate-600 dark:text-slate-400 hover:text-slate-950 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-slate-800'
                                                            }`}
                                                        >
                                                            {p}
                                                        </button>
                                                    ))}
                                                </div>

                                                <button
                                                    type="button"
                                                    onClick={() => setCurrentPage(prev => Math.min(totalPages, prev + 1))}
                                                    disabled={currentPage === totalPages}
                                                    className="h-9 px-4 rounded-xl border border-slate-200 dark:border-slate-800/80 text-slate-600 dark:text-slate-400 hover:text-slate-950 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-slate-800 disabled:opacity-40 disabled:cursor-not-allowed disabled:hover:bg-transparent transition-all flex items-center justify-center gap-1 cursor-pointer font-bold text-[11px] uppercase tracking-widest"
                                                >
                                                    Next
                                                    <span className="material-symbols-outlined text-base">chevron_right</span>
                                                </button>
                                            </div>
                                        </div>
                                    </>
                                )}
                            </>
                        )}
                    </div>
                </div>

                {/* Details Modal */}
                {selectedHistoryItem && (() => {
                    let parsed = {};
                    try {
                        parsed = JSON.parse(selectedHistoryItem.form_data || '{}');
                    } catch (e) {
                        console.error("Failed to parse form_data", e);
                    }
                    const fData = parsed.formData || {};
                    const loansList = parsed.loans || [];
                    const guarantors = parsed.joinees || [];

                    return (
                        <div className="fixed inset-0 z-[250] flex items-center justify-center bg-slate-900/40 dark:bg-black/60 backdrop-blur-sm p-4 overflow-y-auto animate-in fade-in duration-200">
                            <div className="bg-white dark:bg-[#0f172b] rounded-3xl shadow-2xl w-full max-w-5xl border border-slate-200 dark:border-slate-800 my-8 flex flex-col max-h-[90vh] overflow-hidden animate-in zoom-in-95 duration-200">
                                {/* Modal Header */}
                                <div className="flex items-center justify-between px-8 py-6 border-b border-slate-200 dark:border-slate-800/80 bg-slate-50/50 dark:bg-slate-900/10 shrink-0">
                                    <div className="flex items-center gap-4">
                                        <div className="w-12 h-12 rounded-2xl bg-blue-600/10 text-blue-600 dark:text-blue-400 flex items-center justify-center">
                                            <span className="material-symbols-outlined text-2xl">description</span>
                                        </div>
                                        <div className="text-left">
                                            <h3 className="text-lg font-black tracking-tight text-slate-900 dark:text-white uppercase">Document Package Details</h3>
                                            <p className="text-[11px] font-bold text-slate-400 dark:text-slate-500 uppercase tracking-widest mt-0.5">
                                                Generated by <span className="text-slate-600 dark:text-slate-300">{selectedHistoryItem.username}</span> • {formatDate(selectedHistoryItem.generated_at)}
                                            </p>
                                        </div>
                                    </div>
                                    <button
                                        onClick={() => setSelectedHistoryItem(null)}
                                        className="w-10 h-10 rounded-full hover:bg-slate-100 dark:hover:bg-slate-800/80 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 transition-all cursor-pointer flex items-center justify-center border border-transparent hover:border-slate-200 dark:hover:border-slate-700/50"
                                    >
                                        <span className="material-symbols-outlined text-lg">close</span>
                                    </button>
                                </div>

                                {/* Modal Body (Scrollable) */}
                                <div className="flex-1 overflow-y-auto scrollbar-slim p-8 space-y-6 text-left">
                                    {/* Borrower Details Card */}
                                    <div className="p-6 rounded-2xl border border-slate-200 dark:border-slate-800 bg-slate-50/30 dark:bg-[#0c1220] space-y-4">
                                        <h4 className="text-[11px] font-black uppercase tracking-[0.2em] text-slate-400 dark:text-slate-500 flex items-center gap-2">
                                            <span className="material-symbols-outlined text-base">person</span>
                                            Borrower Details
                                        </h4>
                                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                            <div>
                                                <div className="text-[9px] font-black uppercase tracking-wider text-slate-400">Borrower Firm Name</div>
                                                <div className="text-sm font-semibold text-slate-900 dark:text-white uppercase mt-0.5">{fData.companyName || selectedHistoryItem.proprietor_name || '-'}</div>
                                            </div>
                                            <div>
                                                <div className="text-[9px] font-black uppercase tracking-wider text-slate-400">Proprietor Name</div>
                                                <div className="text-sm font-semibold text-slate-900 dark:text-white uppercase mt-0.5">{fData.proprietorName || selectedHistoryItem.proprietor_name || '-'}</div>
                                            </div>
                                            <div>
                                                <div className="text-[9px] font-black uppercase tracking-wider text-slate-400">Father's Name</div>
                                                <div className="text-sm font-semibold text-slate-900 dark:text-white uppercase mt-0.5">{fData.fatherOfProprietor || '-'}</div>
                                            </div>
                                            <div>
                                                <div className="text-[9px] font-black uppercase tracking-wider text-slate-400">Firm PAN</div>
                                                <div className="text-sm font-semibold text-slate-900 dark:text-white uppercase mt-0.5 font-mono">{fData.proprietorPan || '-'}</div>
                                            </div>
                                            <div>
                                                <div className="text-[9px] font-black uppercase tracking-wider text-slate-400">Place</div>
                                                <div className="text-sm font-semibold text-slate-900 dark:text-white uppercase mt-0.5">{fData.place || '-'}</div>
                                            </div>
                                            <div>
                                                <div className="text-[9px] font-black uppercase tracking-wider text-slate-400">Entity Type</div>
                                                <div className="text-sm font-semibold text-slate-900 dark:text-white uppercase mt-0.5">{selectedHistoryItem.entity_type || 'Proprietor'}</div>
                                            </div>
                                        </div>
                                        <div className="border-t border-slate-200/60 dark:border-slate-800/40 pt-3">
                                            <div className="text-[9px] font-black uppercase tracking-wider text-slate-400">Firm Address</div>
                                            <div className="text-sm font-medium text-slate-700 dark:text-slate-300 mt-1 whitespace-pre-wrap leading-relaxed">{fData.companyAddress || '-'}</div>
                                        </div>
                                    </div>

                                    {/* Lender & Loan Details Card */}
                                    <div className="p-6 rounded-2xl border border-slate-200 dark:border-slate-800 bg-slate-50/30 dark:bg-[#0c1220] space-y-4">
                                        <h4 className="text-[11px] font-black uppercase tracking-[0.2em] text-slate-400 dark:text-slate-500 flex items-center gap-2">
                                            <span className="material-symbols-outlined text-base">payments</span>
                                            Lender & Loan Details
                                        </h4>
                                        <div className="space-y-3 max-h-60 overflow-y-auto scrollbar-slim pr-1">
                                            {loansList.length > 0 ? (
                                                loansList.map((loan, lIdx) => (
                                                    <div key={lIdx} className="p-4 rounded-xl border border-slate-200 dark:border-slate-800/80 bg-white dark:bg-slate-800/20 flex flex-col gap-3">
                                                        <div className="text-left min-w-0 flex-1">
                                                            <span className="text-[9px] font-black text-slate-400 uppercase tracking-wider block">Lender #{lIdx + 1}</span>
                                                            <span className="text-sm font-black text-slate-900 dark:text-white uppercase truncate block mt-0.5" title={loan.lenderName}>
                                                                {cleanDisplayLenderName(loan.lenderName)}
                                                            </span>
                                                        </div>
                                                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
                                                            <div>
                                                                <span className="text-[9px] font-black text-slate-400 uppercase tracking-wider block">Principal</span>
                                                                <span className="text-xs font-black text-emerald-600 dark:text-emerald-400 block mt-0.5">₹ {loan.loanAmount || '-'}</span>
                                                            </div>
                                                            <div>
                                                                <span className="text-[9px] font-black text-slate-400 uppercase tracking-wider block">Repayment</span>
                                                                <span className="text-xs font-black text-blue-600 dark:text-blue-400 block mt-0.5">₹ {loan.repayment || '-'}</span>
                                                            </div>
                                                        </div>
                                                    </div>
                                                ))
                                            ) : (
                                                <div className="p-4 rounded-xl border border-slate-200 dark:border-slate-800/80 bg-white dark:bg-[#0c1220] flex justify-between">
                                                    <div className="text-left">
                                                        <span className="text-[9px] font-black text-slate-400 uppercase block">Lender</span>
                                                        <span className="text-sm font-bold text-slate-900 dark:text-white uppercase mt-0.5 block">{selectedHistoryItem.lenders || '-'}</span>
                                                    </div>
                                                    <div className="text-right">
                                                        <span className="text-[9px] font-black text-slate-400 uppercase block">Total Principal</span>
                                                        <span className="text-sm font-black text-emerald-600 dark:text-emerald-400 mt-0.5 block">₹ {selectedHistoryItem.total_loan_amount || '-'}</span>
                                                    </div>
                                                </div>
                                            )}
                                        </div>
                                    </div>

                                    {/* Loan Terms & Schedule Card */}
                                    <div className="p-6 rounded-2xl border border-slate-200 dark:border-slate-800 bg-slate-50/30 dark:bg-[#0c1220] space-y-4">
                                        <h4 className="text-[11px] font-black uppercase tracking-[0.2em] text-slate-400 dark:text-slate-500 flex items-center gap-2">
                                            <span className="material-symbols-outlined text-base">schedule</span>
                                            Loan Terms & Schedule
                                        </h4>
                                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                            <div>
                                                <div className="text-[9px] font-black uppercase tracking-wider text-slate-400">Loan Date</div>
                                                <div className="text-sm font-semibold text-slate-900 dark:text-white mt-0.5">{fData.loanDate || '-'}</div>
                                            </div>
                                            <div>
                                                <div className="text-[9px] font-black uppercase tracking-wider text-slate-400">EMI Start Date</div>
                                                <div className="text-sm font-semibold text-slate-900 dark:text-white mt-0.5">{fData.emiStartDate || '-'}</div>
                                            </div>
                                            <div>
                                                <div className="text-[9px] font-black uppercase tracking-wider text-slate-400">Period Type</div>
                                                <div className="text-sm font-semibold text-slate-900 dark:text-white uppercase mt-0.5">{fData.period || '-'}</div>
                                            </div>
                                            <div>
                                                <div className="text-[9px] font-black uppercase tracking-wider text-slate-400">No. of Periods</div>
                                                <div className="text-sm font-semibold text-slate-900 dark:text-white mt-0.5">{fData.noOfPeriod || '-'}</div>
                                            </div>
                                            <div>
                                                <div className="text-[9px] font-black uppercase tracking-wider text-slate-400">Interest Rate</div>
                                                <div className="text-sm font-semibold text-slate-900 dark:text-white mt-0.5">{fData.interest ? `${fData.interest}%` : '-'}</div>
                                            </div>
                                        </div>
                                    </div>

                                    {/* Banking Details Card */}
                                    <div className="p-6 rounded-2xl border border-slate-200 dark:border-slate-800 bg-slate-50/30 dark:bg-[#0c1220] space-y-4">
                                        <h4 className="text-[11px] font-black uppercase tracking-[0.2em] text-slate-400 dark:text-slate-500 flex items-center gap-2">
                                            <span className="material-symbols-outlined text-base">account_balance</span>
                                            Banking Details
                                        </h4>
                                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                            <div>
                                                <div className="text-[9px] font-black uppercase tracking-wider text-slate-400">Account Number</div>
                                                <div className="text-sm font-semibold text-slate-900 dark:text-white font-mono mt-0.5">{fData.accountNumber || '-'}</div>
                                            </div>
                                            <div>
                                                <div className="text-[9px] font-black uppercase tracking-wider text-slate-400">IFSC Code</div>
                                                <div className="text-sm font-semibold text-slate-900 dark:text-white font-mono mt-0.5">{fData.ifsc || '-'}</div>
                                            </div>
                                            <div>
                                                <div className="text-[9px] font-black uppercase tracking-wider text-slate-400">Bank Name</div>
                                                <div className="text-sm font-semibold text-slate-900 dark:text-white uppercase mt-0.5">{fData.bankName || '-'}</div>
                                            </div>
                                            <div>
                                                <div className="text-[9px] font-black uppercase tracking-wider text-slate-400">Branch & Pincode</div>
                                                <div className="text-sm font-semibold text-slate-900 dark:text-white uppercase mt-0.5">
                                                    {fData.branch ? `${fData.branch} - ${fData.pincode || ''}` : '-'}
                                                </div>
                                            </div>
                                        </div>
                                    </div>

                                    {/* Guarantor Details Card (Conditional) */}
                                    {guarantors.length > 0 && (
                                        <div className="p-6 rounded-2xl border border-slate-200 dark:border-slate-800 bg-slate-50/30 dark:bg-[#0c1220] space-y-4">
                                            <h4 className="text-[11px] font-black uppercase tracking-[0.2em] text-slate-400 dark:text-slate-500 flex items-center gap-2">
                                                <span className="material-symbols-outlined text-base">gpp_good</span>
                                                Guarantor Information
                                            </h4>
                                            <div className="space-y-4 max-h-60 overflow-y-auto scrollbar-slim pr-1">
                                                {guarantors.map((g, gIdx) => (
                                                    <div key={gIdx} className="p-4 rounded-xl border border-slate-200 dark:border-slate-800/80 bg-white dark:bg-slate-800/20 space-y-3 text-left">
                                                        <div className="flex items-center justify-between border-b border-slate-100 dark:border-slate-800/50 pb-2">
                                                            <span className="text-[10px] font-black text-slate-400 uppercase tracking-wider">Guarantor #{gIdx + 1}</span>
                                                            <span className="text-[14px] font-mono font-semibold text-slate-500 dark:text-slate-400 uppercase">{g.pan || 'No PAN'}</span>
                                                        </div>
                                                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
                                                            <div>
                                                                <span className="text-[9px] font-bold text-slate-400 uppercase tracking-wider block">Name</span>
                                                                <span className="font-semibold text-slate-900 dark:text-white uppercase mt-0.5 block">{g.name || '-'}</span>
                                                            </div>
                                                            <div>
                                                                <span className="text-[9px] font-bold text-slate-400 uppercase tracking-wider block">Father's Name</span>
                                                                <span className="font-semibold text-slate-900 dark:text-white uppercase mt-0.5 block">{g.father || '-'}</span>
                                                            </div>
                                                        </div>
                                                        <div>
                                                            <span className="text-[9px] font-bold text-slate-400 uppercase tracking-wider block">Address</span>
                                                            <span className="text-xs font-medium text-slate-700 dark:text-slate-300 mt-1 block leading-relaxed">{g.address || '-'}</span>
                                                        </div>
                                                    </div>
                                                ))}
                                            </div>
                                        </div>
                                    )}
                                </div>
                            </div>
                        </div>
                    );
                })()}

                {/* Delete Confirmation Modal */}
                {showDeleteConfirm && (
                    <div className="fixed inset-0 z-[250] flex items-center justify-center bg-slate-900/40 dark:bg-black/60 backdrop-blur-sm p-4 animate-in fade-in duration-200">
                        <div className="bg-white dark:bg-[#0a0f18] rounded-3xl shadow-2xl w-full max-w-sm overflow-hidden border border-slate-200 dark:border-slate-800 p-8 flex flex-col items-center text-center animate-in zoom-in-95 duration-200">
                            <div className="w-16 h-16 rounded-full bg-red-100 dark:bg-red-600/10 text-red-500 flex items-center justify-center mb-6 border border-red-200 dark:border-red-500/20">
                                <span className="material-symbols-outlined text-[32px]">delete_forever</span>
                            </div>
                            <h3 className="text-xl font-black tracking-tight text-slate-900 dark:text-white mb-2">Delete Log Entry?</h3>
                            <p className="text-slate-500 dark:text-slate-400 text-xs mb-8 leading-relaxed">
                                Are you sure you want to delete this document generation log from history? This action is permanent and cannot be undone.
                            </p>
                            <div className="flex gap-4 w-full">
                                <button
                                    onClick={() => {
                                        setShowDeleteConfirm(false);
                                        setDeleteId(null);
                                    }}
                                    disabled={actionLoading}
                                    className="flex-1 px-4 py-3.5 rounded-xl border border-slate-300 dark:border-slate-800 text-slate-600 dark:text-slate-400 font-bold uppercase tracking-widest text-[10px] hover:text-slate-900 dark:hover:text-white hover:bg-slate-50 dark:hover:bg-slate-800 transition-all cursor-pointer disabled:opacity-50"
                                >
                                    Cancel
                                </button>
                                <button
                                    onClick={confirmDelete}
                                    disabled={actionLoading}
                                    className="flex-1 px-4 py-3.5 rounded-xl bg-red-600 hover:bg-red-700 text-white font-bold uppercase tracking-widest text-[10px] transition-all cursor-pointer shadow-lg shadow-red-600/20 disabled:opacity-50 flex items-center justify-center"
                                >
                                    {actionLoading ? (
                                        <div className="w-4 h-4 border-2 border-white/20 border-t-white rounded-full animate-spin"></div>
                                    ) : (
                                        'Delete'
                                    )}
                                </button>
                            </div>
                        </div>
                    </div>
                )}
            </main>
        </Layout>
    );
}

export default History;
