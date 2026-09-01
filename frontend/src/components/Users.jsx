/**
 * Project: Fin Report - Documents team
 * Author: Dhinakaran Sekar
 * Date: 2026-05-27
 * Description: Premium Users Dashboard component for managing staff users, adding new team members, and reviewing profile setup statuses.
 */

import React, { useState, useEffect } from 'react';
import axios from 'axios';
import Layout from './Layout';
import config from './config';

function Users({ user, onLogout, onTabChange }) {
    const [users, setUsers] = useState([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const [successMessage, setSuccessMessage] = useState(null);
    
    // Edit user modal states
    const [showEditModal, setShowEditModal] = useState(false);
    const [editUser, setEditUser] = useState(null);
    const [editing, setEditing] = useState(false);

    // Add user modal states
    const [showAddModal, setShowAddModal] = useState(false);
    const [newEmpCode, setNewEmpCode] = useState('');
    const [newName, setNewName] = useState('');
    const [newEmail, setNewEmail] = useState('');
    const [newPassword, setNewPassword] = useState('');
    const [newAccessedMenus, setNewAccessedMenus] = useState(['fin-report', 'documat']);
    const [newRole, setNewRole] = useState('user');
    const [adding, setAdding] = useState(false);

    // Delete user confirmation states
    const [userToDelete, setUserToDelete] = useState(null);
    const [deleting, setDeleting] = useState(false);

    // Pagination states
    const [currentPage, setCurrentPage] = useState(1);
    const ITEMS_PER_PAGE = 5;

    useEffect(() => {
        setCurrentPage(1);
    }, [users]);

    // Load users from backend
    const fetchUsers = async () => {
        setLoading(true);
        setError(null);
        try {
            const response = await axios.get(`${config.API_BASE_URL}/api/users/`);
            if (response.data && response.data.success) {
                setUsers(response.data.users);
            } else {
                setError(response.data.message || 'Failed to load users');
            }
        } catch (err) {
            console.error('Error fetching users:', err);
            setError(err.response?.data?.message || 'Failed to connect to the server');
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchUsers();
    }, []);

    // Create user handler
    const handleAddUser = async (e) => {
        e.preventDefault();
        if (!newEmpCode.trim() || !newName.trim()) return;

        setAdding(true);
        setError(null);
        try {
            const response = await axios.post(`${config.API_BASE_URL}/api/users/`, {
                employee_code: newEmpCode.trim().toUpperCase(),
                name: newName.trim(),
                email: newEmail.trim(),
                password: newPassword.trim(),
                accessed_menus: newAccessedMenus,
                role: newRole
            });

            if (response.data && response.data.success) {
                setSuccessMessage('User added successfully!');
                setShowAddModal(false);
                setNewEmpCode('');
                setNewName('');
                setNewEmail('');
                setNewPassword('');
                setNewAccessedMenus(['fin-report', 'documat']);
                setNewRole('user');
                fetchUsers();
                
                // Clear success message after 5 seconds
                setTimeout(() => setSuccessMessage(null), 5000);
            } else {
                setError(response.data.message || 'Failed to create user');
            }
        } catch (err) {
            console.error('Error creating user:', err);
            setError(err.response?.data?.message || 'Failed to create user');
        } finally {
            setAdding(false);
        }
    };

    // Edit user handler
    const handleEditUser = async (e) => {
        e.preventDefault();
        if (!editUser.employee_code.trim() || !editUser.name.trim()) return;

        setEditing(true);
        setError(null);
        try {
            const response = await axios.put(`${config.API_BASE_URL}/api/users/${editUser.id}`, {
                employee_code: editUser.employee_code.trim().toUpperCase(),
                name: editUser.name.trim(),
                email: editUser.email.trim(),
                password: editUser.password.trim(),
                accessed_menus: editUser.accessed_menus,
                role: editUser.role
            });

            if (response.data && response.data.success) {
                setSuccessMessage('User updated successfully!');
                setShowEditModal(false);
                setEditUser(null);
                fetchUsers();
                
                setTimeout(() => setSuccessMessage(null), 5000);
            } else {
                setError(response.data.message || 'Failed to update user');
            }
        } catch (err) {
            console.error('Error updating user:', err);
            setError(err.response?.data?.message || 'Failed to update user');
        } finally {
            setEditing(false);
        }
    };

    // Delete user handler
    const handleDeleteUser = async () => {
        if (!userToDelete) return;

        setDeleting(true);
        setError(null);
        try {
            const response = await axios.delete(`${config.API_BASE_URL}/api/users/${userToDelete.id}`);
            if (response.data && response.data.success) {
                setSuccessMessage(`User "${userToDelete.name}" deleted successfully.`);
                setUserToDelete(null);
                fetchUsers();
                
                // Clear success message after 5 seconds
                setTimeout(() => setSuccessMessage(null), 5000);
            } else {
                setError(response.data.message || 'Failed to delete user');
            }
        } catch (err) {
            console.error('Error deleting user:', err);
            setError(err.response?.data?.message || 'Failed to delete user');
        } finally {
            setDeleting(false);
        }
    };

    const totalPages = Math.max(1, Math.ceil(users.length / ITEMS_PER_PAGE));
    const pagedUsers = users.slice((currentPage - 1) * ITEMS_PER_PAGE, currentPage * ITEMS_PER_PAGE);
    const startRecord = users.length > 0 ? (currentPage - 1) * ITEMS_PER_PAGE + 1 : 0;
    const endRecord = Math.min(currentPage * ITEMS_PER_PAGE, users.length);

    return (
        <Layout user={user} onLogout={onLogout} onTabChange={onTabChange} activeTab="users">
            <main className="flex-1 flex flex-col bg-slate-50 dark:bg-[#101822] px-10 pt-10 pb-8 transition-colors duration-300 h-full overflow-hidden">
                <div className="flex-1 flex flex-col min-h-0">
                    {/* Header Section */}
                    <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-6 shrink-0">
                        <div className="flex flex-col items-start text-left gap-2 max-w-3xl">
                            <h1 className="text-4xl font-black tracking-tight text-slate-900 dark:text-white transition-colors duration-300">Users</h1>
                        </div>
                        <button
                            onClick={() => setShowAddModal(true)}
                            className="flex items-center justify-center gap-3 px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-2xl font-bold uppercase tracking-widest text-[11px] transition-all cursor-pointer shadow-xl shadow-blue-600/20 active:scale-95 shrink-0 self-start md:self-center"
                        >
                            <span className="material-symbols-outlined text-lg">person_add</span>
                            Add User
                        </button>
                    </div>

                    {/* Status Feedback Banners */}
                    {error && (
                        <div className="mb-6 bg-red-500/10 border border-red-500/20 text-red-500 px-6 py-4 rounded-2xl flex items-center gap-4 animate-in fade-in slide-in-from-top-2 shrink-0">
                            <span className="material-symbols-outlined text-2xl">error_outline</span>
                            <span className="text-[12px] font-bold flex-1 tracking-widest">{error}</span>
                            <button
                                onClick={() => setError(null)}
                                className="flex items-center justify-center h-8 w-8 rounded-lg hover:bg-red-500/20 transition-colors"
                            >
                                <span className="material-symbols-outlined text-xl">close</span>
                            </button>
                        </div>
                    )}

                    {successMessage && (
                        <div className="mb-6 bg-emerald-500/10 border border-emerald-500/20 text-emerald-600 dark:text-emerald-400 px-6 py-4 rounded-2xl flex items-center gap-4 animate-in fade-in slide-in-from-top-2 shrink-0">
                            <span className="material-symbols-outlined text-2xl">check_circle</span>
                            <span className="text-[12px] font-bold flex-1 tracking-widest">{successMessage}</span>
                            <button
                                onClick={() => setSuccessMessage(null)}
                                className="flex items-center justify-center h-8 w-8 rounded-lg hover:bg-emerald-500/20 transition-colors"
                            >
                                <span className="material-symbols-outlined text-xl">close</span>
                            </button>
                        </div>
                    )}

                    {/* Users Data Card */}
                    <div className="flex-1 flex flex-col min-h-0 bg-white dark:bg-[#0f172b] rounded-3xl shadow-2xl border border-slate-200 dark:border-slate-800 overflow-hidden transition-colors duration-300">
                        {loading && users.length === 0 ? (
                            <div className="flex flex-col items-center justify-center py-20 gap-4">
                                <div className="w-10 h-10 border-4 border-blue-600/30 border-t-blue-600 rounded-full animate-spin" />
                                <span className="text-[11px] font-black uppercase tracking-[0.2em] text-slate-400">Loading Users...</span>
                            </div>
                        ) : users.length === 0 ? (
                            <div className="flex flex-col items-center justify-center py-20 gap-4 text-center">
                                <div className="w-16 h-16 rounded-full bg-slate-100 dark:bg-slate-800 flex items-center justify-center text-slate-400">
                                    <span className="material-symbols-outlined text-4xl">group_off</span>
                                </div>
                                <div>
                                    <h4 className="text-xl font-bold text-slate-900 dark:text-white mb-1">No users found</h4>
                                    <p className="text-slate-500 text-sm">Get started by creating a new staff account.</p>
                                </div>
                            </div>
                        ) : (
                            <>
                                {/* Fixed column header */}
                                <div className="shrink-0 bg-slate-50/90 dark:bg-slate-900/40 border-b border-slate-200 dark:border-slate-800/80">
                                    <table className="w-full border-collapse text-left table-fixed">
                                        <colgroup>
                                            <col style={{width:'20%'}} />
                                            <col style={{width:'12%'}} />
                                            <col style={{width:'8%'}} />
                                            <col style={{width:'14%'}} />
                                            <col style={{width:'10%'}} />
                                            <col style={{width:'10%'}} />
                                        </colgroup>
                                        <thead>
                                            <tr className="text-slate-500 dark:text-slate-400 text-[11px] font-black uppercase tracking-[0.2em]">
                                                <th className="py-6 px-8">Staff Member</th>
                                                <th className="py-6 px-6">Employee Code</th>
                                                <th className="py-6 px-6">Role</th>
                                                <th className="py-6 px-6">Accessed Menus</th>
                                                <th className="py-6 px-6">Status</th>
                                                <th className="py-6 px-8 text-right">Actions</th>
                                            </tr>
                                        </thead>
                                    </table>
                                </div>

                                {/* Scrollable body container */}
                                <div className="flex-1 overflow-x-auto overflow-y-auto scrollbar-slim">
                                    <table className="w-full border-collapse text-left table-fixed">
                                        <colgroup>
                                            <col style={{width:'20%'}} />
                                            <col style={{width:'12%'}} />
                                            <col style={{width:'8%'}} />
                                            <col style={{width:'14%'}} />
                                            <col style={{width:'10%'}} />
                                            <col style={{width:'10%'}} />
                                        </colgroup>
                                        <tbody className="divide-y divide-slate-100 dark:divide-slate-800/60">
                                            {pagedUsers.map((u) => {
                                                const isSelf = u.employee_code === user?.employee_code;
                                                return (
                                                    <tr key={u.id} className="hover:bg-slate-50/55 dark:hover:bg-slate-800/20 transition-colors duration-200">
                                                        <td className="py-5 px-8">
                                                            <div className="flex items-center gap-4">
                                                                <div className="flex flex-col min-w-0">
                                                                    <span className="text-[15px] font-bold text-slate-950 dark:text-white flex items-center gap-2 truncate capitalize">
                                                                        {u.name}
                                                                        {isSelf && (
                                                                            <span className="px-2 py-0.5 bg-blue-600/10 text-blue-600 dark:text-blue-400 text-[10px] font-black uppercase tracking-widest rounded-full shrink-0">
                                                                                You
                                                                            </span>
                                                                        )}
                                                                    </span>
                                                                    <span className="text-[11px] font-medium text-slate-400 dark:text-slate-500 truncate" title={u.email}>
                                                                        {u.email || `System ID: #${u.id}`}
                                                                    </span>
                                                                </div>
                                                            </div>
                                                        </td>
                                                        <td className="py-5 px-6 font-mono text-[13px] font-bold text-slate-600 dark:text-slate-400 truncate">
                                                            {u.employee_code}
                                                        </td>
                                                        <td className="py-5 px-6">
                                                            <span className={`inline-flex items-center px-3 py-1 rounded-full text-[10px] font-black uppercase tracking-widest ${u.role === 'admin' ? 'bg-amber-500/10 text-amber-500 border border-amber-500/20' : 'bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400'}`}>
                                                                {u.role}
                                                            </span>
                                                        </td>
                                                        <td className="py-5 px-6">
                                                            <div className="flex flex-wrap gap-1">
                                                                {(!u.accessed_menus || u.accessed_menus.includes('fin-report')) && (
                                                                    <span className="px-2 py-0.5 bg-blue-600/10 text-blue-600 dark:text-blue-400 text-[10px] font-black uppercase tracking-widest rounded-md border border-blue-600/20">
                                                                        Fin Report
                                                                    </span>
                                                                )}
                                                                {(!u.accessed_menus || u.accessed_menus.includes('documat')) && (
                                                                    <span className="px-2 py-0.5 bg-indigo-600/10 text-indigo-600 dark:text-indigo-400 text-[10px] font-black uppercase tracking-widest rounded-md border border-indigo-600/20">
                                                                        Documat
                                                                    </span>
                                                                )}
                                                                {u.accessed_menus && !u.accessed_menus.includes('fin-report') && !u.accessed_menus.includes('documat') && (
                                                                    <span className="px-2 py-0.5 bg-slate-100 dark:bg-slate-800 text-slate-400 text-[10px] font-black uppercase tracking-widest rounded-md">
                                                                        None
                                                                    </span>
                                                                )}
                                                            </div>
                                                        </td>
                                                        <td className="py-5 px-6">
                                                            <div className="flex items-center gap-2">
                                                                <div className={`w-2 h-2 rounded-full ${!u.is_initial_password ? 'bg-emerald-500' : 'bg-amber-400 animate-pulse'}`} />
                                                                <span className="text-xs font-bold text-slate-600 dark:text-slate-400">
                                                                    {!u.is_initial_password ? 'Configured' : 'Awaiting Setup'}
                                                                </span>
                                                            </div>
                                                        </td>
                                                        <td className="py-5 px-8 text-right">
                                                            <div className="flex items-center justify-end gap-1">
                                                                <button
                                                                    onClick={() => {
                                                                        setEditUser({
                                                                            ...u,
                                                                            accessed_menus: u.accessed_menus ? u.accessed_menus.split(',') : ['fin-report', 'documat'],
                                                                            password: ''
                                                                        });
                                                                        setShowEditModal(true);
                                                                    }}
                                                                    className="h-9 w-9 inline-flex items-center justify-center rounded-xl bg-slate-100 hover:bg-blue-50 dark:bg-slate-800/80 dark:hover:bg-blue-500/10 text-slate-500 hover:text-blue-600 dark:text-slate-400 dark:hover:text-blue-400 transition-all duration-200 cursor-pointer border border-slate-200/40 dark:border-slate-700/50"
                                                                    title="Edit User"
                                                                >
                                                                    <span className="material-symbols-outlined text-[18px]">edit</span>
                                                                </button>
                                                                {!isSelf ? (
                                                                    <button
                                                                        onClick={() => setUserToDelete(u)}
                                                                        className="h-9 w-9 inline-flex items-center justify-center rounded-xl bg-slate-100 hover:bg-red-50 dark:bg-slate-800/80 dark:hover:bg-red-500/10 text-slate-500 hover:text-red-600 dark:text-slate-400 dark:hover:text-red-400 transition-all duration-200 cursor-pointer border border-slate-200/40 dark:border-slate-700/50"
                                                                        title="Delete User"
                                                                    >
                                                                        <span className="material-symbols-outlined text-[18px]">delete</span>
                                                                    </button>
                                                                ) : (
                                                                    <button
                                                                        disabled
                                                                        className="h-9 w-9 inline-flex items-center justify-center rounded-xl bg-slate-100/50 dark:bg-slate-800/30 text-slate-300 dark:text-slate-700 cursor-not-allowed border border-slate-200/20 dark:border-slate-800/30"
                                                                        title="Cannot delete your own active account"
                                                                    >
                                                                        <span className="material-symbols-outlined text-[18px]">delete</span>
                                                                    </button>
                                                                )}
                                                            </div>
                                                        </td>
                                                    </tr>
                                                );
                                            })}
                                        </tbody>
                                    </table>
                                </div>

                                {/* Pagination Controls */}
                                <div className="shrink-0 flex flex-col sm:flex-row items-center justify-between gap-4 px-8 py-5 border-t border-slate-200 dark:border-slate-800/80 bg-slate-50/50 dark:bg-slate-900/10 transition-colors duration-300">
                                    <div className="text-[11px] font-black uppercase tracking-[0.2em] text-slate-400 dark:text-slate-500">
                                        Showing <span className="text-slate-950 dark:text-white font-bold">{startRecord}</span> to <span className="text-slate-950 dark:text-white font-bold">{endRecord}</span> of <span className="text-slate-950 dark:text-white font-bold">{users.length}</span> records
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
                    </div>
                </div>
            </main>

            {/* Add User Modal */}
            {showAddModal && (
                <div className="fixed inset-0 z-[120] flex items-center justify-center bg-slate-900/40 dark:bg-black/60 backdrop-blur-sm p-4 animate-in fade-in duration-200">
                    <form 
                        onSubmit={handleAddUser}
                        className="bg-white dark:bg-[#0a0f18] rounded-3xl shadow-2xl w-full max-w-lg overflow-hidden border border-slate-200 dark:border-slate-800 p-8 flex flex-col animate-in zoom-in-95 duration-200"
                    >
                        <h3 className="text-2xl font-black tracking-tight text-slate-900 dark:text-white mb-6">Add New User</h3>
                        
                        <div className="flex flex-col gap-5 mb-8">
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
                                <div className="flex flex-col gap-2">
                                    <label className="block text-[11px] font-black uppercase tracking-[0.2em] text-slate-500 ml-1">Employee Code</label>
                                    <input
                                        type="text"
                                        required
                                        placeholder="e.g. JB1045"
                                        value={newEmpCode}
                                        onChange={(e) => setNewEmpCode(e.target.value)}
                                        className="w-full px-6 py-4 rounded-2xl bg-slate-50 dark:bg-[#101726] border border-slate-200 dark:border-slate-800 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all font-mono text-[13px] uppercase"
                                    />
                                </div>

                                <div className="flex flex-col gap-2">
                                    <label className="block text-[11px] font-black uppercase tracking-[0.2em] text-slate-500 ml-1">Full Name</label>
                                    <input
                                        type="text"
                                        required
                                        placeholder="Enter full name"
                                        value={newName}
                                        onChange={(e) => setNewName(e.target.value)}
                                        className="w-full px-6 py-4 rounded-2xl bg-slate-50 dark:bg-[#101726] border border-slate-200 dark:border-slate-800 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all text-[13px] capitalize"
                                    />
                                </div>
                            </div>

                            <div className="flex flex-col gap-2">
                                <label className="block text-[11px] font-black uppercase tracking-[0.2em] text-slate-500 ml-1">Email Address</label>
                                <input
                                    type="email"
                                    required
                                    placeholder="e.g. staff@jubilantenterprises.in"
                                    value={newEmail}
                                    onChange={(e) => setNewEmail(e.target.value)}
                                    className="w-full px-6 py-4 rounded-2xl bg-slate-50 dark:bg-[#101726] border border-slate-200 dark:border-slate-800 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all text-[13px]"
                                />
                            </div>

                            <div className="flex flex-col gap-2">
                                <label className="block text-[11px] font-black uppercase tracking-[0.2em] text-slate-500 ml-1">Temporary Password</label>
                                <input
                                    type="text"
                                    placeholder="Enter temporary password (defaults to 123456)"
                                    value={newPassword}
                                    onChange={(e) => setNewPassword(e.target.value)}
                                    className="w-full px-6 py-4 rounded-2xl bg-slate-50 dark:bg-[#101726] border border-slate-200 dark:border-slate-800 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all text-[13px]"
                                />
                            </div>

                            <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
                                <div className="flex flex-col gap-2">
                                    <label className="block text-[11px] font-black uppercase tracking-[0.2em] text-slate-500 ml-1">Security Role</label>
                                    <div className="relative">
                                        <select
                                            value={newRole}
                                            onChange={(e) => setNewRole(e.target.value)}
                                            className="w-full px-6 py-4 rounded-2xl bg-slate-50 dark:bg-[#101726] border border-slate-200 dark:border-slate-800 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all appearance-none cursor-pointer font-bold text-[13px]"
                                        >
                                            <option value="user">Staff Member (User)</option>
                                            <option value="admin">System Administrator (Admin)</option>
                                        </select>
                                        <span className="material-symbols-outlined absolute right-6 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none">
                                            keyboard_arrow_down
                                        </span>
                                    </div>
                                </div>

                                <div className="flex flex-col gap-2">
                                    <label className="block text-[11px] font-black uppercase tracking-[0.2em] text-slate-500 ml-1">Accessed Menus</label>
                                    <div className="relative">
                                        <select
                                            value={
                                                newAccessedMenus.includes('fin-report') && newAccessedMenus.includes('documat') ? 'both' :
                                                newAccessedMenus.includes('fin-report') ? 'fin-report' :
                                                newAccessedMenus.includes('documat') ? 'documat' : 'none'
                                            }
                                            onChange={(e) => {
                                                const val = e.target.value;
                                                if (val === 'both') {
                                                    setNewAccessedMenus(['fin-report', 'documat']);
                                                } else if (val === 'fin-report') {
                                                    setNewAccessedMenus(['fin-report']);
                                                } else if (val === 'documat') {
                                                    setNewAccessedMenus(['documat']);
                                                } else {
                                                    setNewAccessedMenus([]);
                                                }
                                            }}
                                            className="w-full px-6 py-4 rounded-2xl bg-slate-50 dark:bg-[#101726] border border-slate-200 dark:border-slate-800 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all appearance-none cursor-pointer font-bold text-[13px]"
                                        >
                                            <option value="both">Both (Fin Report & Documat)</option>
                                            <option value="fin-report">Fin Report Only</option>
                                            <option value="documat">Documat Only</option>
                                            <option value="none">None</option>
                                        </select>
                                        <span className="material-symbols-outlined absolute right-6 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none">
                                            keyboard_arrow_down
                                        </span>
                                    </div>
                                </div>
                            </div>
                        </div>

                        <div className="flex gap-4">
                            <button
                                type="button"
                                onClick={() => setShowAddModal(false)}
                                className="flex-1 px-6 py-4 rounded-xl border border-slate-300 dark:border-slate-800 text-slate-600 dark:text-slate-400 font-bold uppercase tracking-widest text-[11px] hover:text-slate-900 dark:hover:text-white hover:bg-slate-50 dark:hover:bg-slate-800 transition-all cursor-pointer"
                            >
                                Cancel
                            </button>
                            <button
                                type="submit"
                                disabled={adding}
                                className="flex-1 px-6 py-4 rounded-xl bg-blue-600 hover:bg-blue-700 disabled:opacity-75 disabled:cursor-not-allowed text-white font-bold uppercase tracking-widest text-[11px] transition-all cursor-pointer shadow-xl shadow-blue-600/20 flex items-center justify-center gap-2"
                            >
                                {adding ? (
                                    <>
                                        <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                                        Adding...
                                    </>
                                ) : (
                                    'Create'
                                )}
                            </button>
                        </div>
                    </form>
                </div>
            )}

            {/* Edit User Modal */}
            {showEditModal && editUser && (
                <div className="fixed inset-0 z-[120] flex items-center justify-center bg-slate-900/40 dark:bg-black/60 backdrop-blur-sm p-4 animate-in fade-in duration-200">
                    <form 
                        onSubmit={handleEditUser}
                        className="bg-white dark:bg-[#0a0f18] rounded-3xl shadow-2xl w-full max-w-lg overflow-hidden border border-slate-200 dark:border-slate-800 p-8 flex flex-col animate-in zoom-in-95 duration-200"
                    >
                        <h3 className="text-2xl font-black tracking-tight text-slate-900 dark:text-white mb-6">Edit User</h3>
                        
                        <div className="flex flex-col gap-5 mb-8">
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
                                <div className="flex flex-col gap-2">
                                    <label className="block text-[11px] font-black uppercase tracking-[0.2em] text-slate-500 ml-1">Employee Code</label>
                                    <input
                                        type="text"
                                        required
                                        placeholder="e.g. JB1045"
                                        value={editUser.employee_code}
                                        onChange={(e) => setEditUser({...editUser, employee_code: e.target.value})}
                                        className="w-full px-6 py-4 rounded-2xl bg-slate-50 dark:bg-[#101726] border border-slate-200 dark:border-slate-800 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all font-mono text-[13px] uppercase"
                                    />
                                </div>

                                <div className="flex flex-col gap-2">
                                    <label className="block text-[11px] font-black uppercase tracking-[0.2em] text-slate-500 ml-1">Full Name</label>
                                    <input
                                        type="text"
                                        required
                                        placeholder="Enter full name"
                                        value={editUser.name}
                                        onChange={(e) => setEditUser({...editUser, name: e.target.value})}
                                        className="w-full px-6 py-4 rounded-2xl bg-slate-50 dark:bg-[#101726] border border-slate-200 dark:border-slate-800 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all text-[13px] capitalize"
                                    />
                                </div>
                            </div>

                            <div className="flex flex-col gap-2">
                                <label className="block text-[11px] font-black uppercase tracking-[0.2em] text-slate-500 ml-1">Email Address</label>
                                <input
                                    type="email"
                                    required
                                    placeholder="e.g. staff@jubilantenterprises.in"
                                    value={editUser.email || ''}
                                    onChange={(e) => setEditUser({...editUser, email: e.target.value})}
                                    className="w-full px-6 py-4 rounded-2xl bg-slate-50 dark:bg-[#101726] border border-slate-200 dark:border-slate-800 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all text-[13px]"
                                />
                            </div>

                            <div className="flex flex-col gap-2">
                                <label className="block text-[11px] font-black uppercase tracking-[0.2em] text-slate-500 ml-1">New Password (Optional)</label>
                                <input
                                    type="text"
                                    placeholder="Leave blank to keep current password"
                                    value={editUser.password || ''}
                                    onChange={(e) => setEditUser({...editUser, password: e.target.value})}
                                    className="w-full px-6 py-4 rounded-2xl bg-slate-50 dark:bg-[#101726] border border-slate-200 dark:border-slate-800 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all text-[13px]"
                                />
                            </div>

                            <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
                                <div className="flex flex-col gap-2">
                                    <label className="block text-[11px] font-black uppercase tracking-[0.2em] text-slate-500 ml-1">Security Role</label>
                                    <div className="relative">
                                        <select
                                            value={editUser.role}
                                            onChange={(e) => setEditUser({...editUser, role: e.target.value})}
                                            className="w-full px-6 py-4 rounded-2xl bg-slate-50 dark:bg-[#101726] border border-slate-200 dark:border-slate-800 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all appearance-none cursor-pointer font-bold text-[13px]"
                                        >
                                            <option value="user">Staff Member (User)</option>
                                            <option value="admin">System Administrator (Admin)</option>
                                        </select>
                                        <span className="material-symbols-outlined absolute right-6 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none">
                                            keyboard_arrow_down
                                        </span>
                                    </div>
                                </div>

                                <div className="flex flex-col gap-2">
                                    <label className="block text-[11px] font-black uppercase tracking-[0.2em] text-slate-500 ml-1">Accessed Menus</label>
                                    <div className="relative">
                                        <select
                                            value={
                                                editUser.accessed_menus.includes('fin-report') && editUser.accessed_menus.includes('documat') ? 'both' :
                                                editUser.accessed_menus.includes('fin-report') ? 'fin-report' :
                                                editUser.accessed_menus.includes('documat') ? 'documat' : 'none'
                                            }
                                            onChange={(e) => {
                                                const val = e.target.value;
                                                let newMenus = [];
                                                if (val === 'both') {
                                                    newMenus = ['fin-report', 'documat'];
                                                } else if (val === 'fin-report') {
                                                    newMenus = ['fin-report'];
                                                } else if (val === 'documat') {
                                                    newMenus = ['documat'];
                                                }
                                                setEditUser({...editUser, accessed_menus: newMenus});
                                            }}
                                            className="w-full px-6 py-4 rounded-2xl bg-slate-50 dark:bg-[#101726] border border-slate-200 dark:border-slate-800 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all appearance-none cursor-pointer font-bold text-[13px]"
                                        >
                                            <option value="both">Both (Fin Report & Documat)</option>
                                            <option value="fin-report">Fin Report Only</option>
                                            <option value="documat">Documat Only</option>
                                            <option value="none">None</option>
                                        </select>
                                        <span className="material-symbols-outlined absolute right-6 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none">
                                            keyboard_arrow_down
                                        </span>
                                    </div>
                                </div>
                            </div>
                        </div>

                        <div className="flex gap-4">
                            <button
                                type="button"
                                onClick={() => setShowEditModal(false)}
                                className="flex-1 px-6 py-4 rounded-xl border border-slate-300 dark:border-slate-800 text-slate-600 dark:text-slate-400 font-bold uppercase tracking-widest text-[11px] hover:text-slate-900 dark:hover:text-white hover:bg-slate-50 dark:hover:bg-slate-800 transition-all cursor-pointer"
                            >
                                Cancel
                            </button>
                            <button
                                type="submit"
                                disabled={editing}
                                className="flex-1 px-6 py-4 rounded-xl bg-blue-600 hover:bg-blue-700 disabled:opacity-75 disabled:cursor-not-allowed text-white font-bold uppercase tracking-widest text-[11px] transition-all cursor-pointer shadow-xl shadow-blue-600/20 flex items-center justify-center gap-2"
                            >
                                {editing ? (
                                    <>
                                        <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                                        Updating...
                                    </>
                                ) : (
                                    'Update'
                                )}
                            </button>
                        </div>
                    </form>
                </div>
            )}

            {/* Delete Confirmation Modal */}
            {userToDelete && (
                <div className="fixed inset-0 z-[120] flex items-center justify-center bg-slate-900/40 dark:bg-black/60 backdrop-blur-sm p-4 animate-in fade-in duration-200">
                    <div className="bg-white dark:bg-[#0a0f18] rounded-3xl shadow-2xl w-full max-w-sm overflow-hidden border border-slate-200 dark:border-slate-800 p-10 flex flex-col items-center text-center animate-in zoom-in-95 duration-200">
                        <div className="w-20 h-20 rounded-full bg-red-100 dark:bg-red-600/10 text-red-500 flex items-center justify-center mb-8 border border-red-200 dark:border-red-500/20">
                            <span className="material-symbols-outlined text-[40px]">person_remove</span>
                        </div>
                        <h3 className="text-2xl font-black tracking-tight text-slate-900 dark:text-white mb-2">Delete User?</h3>
                        <p className="text-slate-600 dark:text-slate-400 text-sm mb-10 leading-relaxed">
                            Are you sure you want to delete <span className="font-bold text-slate-900 dark:text-white">"{userToDelete.name}"</span>? This action is permanent and cannot be undone.
                        </p>
                        <div className="flex gap-4 w-full">
                            <button
                                onClick={() => setUserToDelete(null)}
                                className="flex-1 px-6 py-4 rounded-xl border border-slate-300 dark:border-slate-800 text-slate-600 dark:text-slate-400 font-bold uppercase tracking-widest text-[11px] hover:text-slate-900 dark:hover:text-white hover:bg-slate-50 dark:hover:bg-slate-800 transition-all cursor-pointer"
                            >
                                Keep User
                            </button>
                            <button
                                onClick={handleDeleteUser}
                                disabled={deleting}
                                className="flex-1 px-6 py-4 rounded-xl bg-red-600 hover:bg-red-700 disabled:opacity-75 disabled:cursor-not-allowed text-white font-bold uppercase tracking-widest text-[11px] transition-all cursor-pointer shadow-xl shadow-red-600/20 flex items-center justify-center gap-2"
                            >
                                {deleting ? (
                                    <>
                                        <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                                        Deleting...
                                    </>
                                ) : (
                                    'Delete'
                                )}
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </Layout>
    );
}

export default Users;
