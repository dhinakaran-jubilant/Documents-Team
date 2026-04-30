import React, { useState, useEffect } from 'react';
import logoImage from '../assets/logo.png';

const Layout = ({ children, user, onLogout, activeTab = 'contra-match', breadcrumbs = [] }) => {
    const [showLogoutConfirm, setShowLogoutConfirm] = useState(false);
    const [isDark, setIsDark] = useState(() => {
        return localStorage.getItem('isDark') === 'true' || true; // Default to dark for premium feel
    });

    useEffect(() => {
        if (isDark) {
            document.documentElement.classList.add('dark');
        } else {
            document.documentElement.classList.remove('dark');
        }
    }, [isDark]);

    const toggleTheme = () => {
        setIsDark(prev => {
            const next = !prev;
            localStorage.setItem('isDark', String(next));
            return next;
        });
    };
    const initials = user?.name ? user.name.split(' ').map(n => n[0]).join('').toUpperCase() : 'JD';

    return (
        <div className="relative flex h-screen w-full flex-col overflow-hidden bg-slate-50 dark:bg-[#0f172b] text-slate-800 dark:text-slate-300 font-[Inter] transition-colors duration-300">
            {/* Top Navigation Bar */}
            <header className="flex h-[72px] items-center justify-between border-b border-slate-200 dark:border-slate-800/50 bg-white dark:bg-[#0f172b] px-10 shrink-0 transition-colors duration-300">
                <div className="flex items-center gap-4">
                    <img src={logoImage} alt="Jubilant Group Logo" className="h-10 w-auto object-contain" />
                    <h2 className="text-xl font-extrabold tracking-tight mt-1 bg-gradient-to-r from-[#cbb161] via-[#d4af37] to-[#8a712c] text-transparent bg-clip-text drop-shadow-sm">JUBILANT GROUP</h2>
                </div>
                <div className="flex items-center gap-3">
                    <button
                        onClick={toggleTheme}
                        className="flex items-center justify-center rounded-lg h-10 w-10 hover:bg-slate-100 dark:hover:bg-slate-800/50 transition-colors cursor-pointer"
                    >
                        <span className="material-symbols-outlined text-slate-500 dark:text-slate-400" title='Theme Switch'>
                            {isDark ? 'light_mode' : 'dark_mode'}
                        </span>
                    </button>
                    <button className="flex items-center justify-center rounded-lg h-10 w-10 hover:bg-slate-100 dark:hover:bg-slate-800/50 transition-colors cursor-pointer">
                        <span className="material-symbols-outlined text-slate-500 dark:text-slate-400" title='Notifications'>notifications</span>
                    </button>
                    <button className="flex items-center justify-center rounded-lg h-10 w-10 hover:bg-slate-100 dark:hover:bg-slate-800/50 transition-colors cursor-pointer">
                        <span className="material-symbols-outlined text-slate-500 dark:text-slate-400" title='Help'>help_outline</span>
                    </button>
                </div>
            </header>

            <div className="flex flex-1 overflow-hidden">
                {/* Sidebar */}
                <aside className="w-[260px] border-r border-slate-200 dark:border-slate-800/50 bg-white dark:bg-[#0f172b] flex flex-col shrink-0 transition-colors duration-300">
                    <div className="flex flex-col gap-2 p-4">
                        <div
                            className={`flex items-center gap-3 px-6 h-14 rounded-2xl transition-all cursor-pointer ${activeTab === 'fin-report'
                                ? 'bg-blue-600 text-white shadow-lg shadow-blue-600/20'
                                : 'text-slate-600 dark:text-slate-500 hover:text-slate-900 dark:hover:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800/30'}`}
                        >
                            <span className="material-symbols-outlined">table_view</span>
                            <span className="text-[12px] font-black uppercase tracking-[0.2em]">Fin Report</span>
                        </div>
                    </div>

                    <div className="mt-auto p-4 border-t border-slate-200 dark:border-slate-800/50 bg-white dark:bg-[#0f172b] transition-colors duration-300">
                        <div className="flex items-center gap-3">
                            <div className="w-10 h-10 rounded-full bg-blue-600 flex items-center justify-center text-white font-bold text-xs ring-4 ring-blue-600/10 shrink-0">
                                {initials}
                            </div>
                            <div className="flex-1 overflow-hidden">
                                <p className="text-slate-900 dark:text-white text-[14px] font-bold truncate" title={user?.name}>{user?.name || 'User'}</p>
                                <p className="text-[10px] text-slate-500 font-bold uppercase tracking-widest truncate">{user?.role || 'Staff'}</p>
                            </div>
                            <button
                                onClick={() => setShowLogoutConfirm(true)}
                                className="text-slate-400 hover:text-slate-900 dark:text-slate-500 dark:hover:text-white transition-colors cursor-pointer p-1"
                                title="Logout"
                            >
                                <span className="material-symbols-outlined text-lg">logout</span>
                            </button>
                        </div>
                    </div>
                </aside>

                {/* Content Area */}
                <div className="flex-1 flex flex-col relative overflow-hidden bg-slate-50 dark:bg-[#101822] transition-colors duration-300">
                    <div className="flex-1 overflow-y-auto relative scrollbar-slim">
                        {/* Breadcrumbs */}
                        <div className="h-[60px] flex items-center px-10 shrink-0">
                            <div className="flex items-center gap-1 text-blue-500 font-bold text-[12px] uppercase tracking-widest">
                                <span>Home</span>
                                {breadcrumbs.map((crumb, idx) => (
                                    <React.Fragment key={idx}>
                                        <span className="material-symbols-outlined text-sm opacity-50 text-slate-500">chevron_right</span>
                                        <span className={idx === breadcrumbs.length - 1 ? 'text-slate-400' : 'hover:text-blue-400 cursor-pointer'}>
                                            {crumb}
                                        </span>
                                    </React.Fragment>
                                ))}
                            </div>
                        </div>

                        {children}
                    </div>
                </div>
            </div>

            {/* Logout Confirmation Modal */}
            {showLogoutConfirm && (
                <div className="fixed inset-0 z-[150] flex items-center justify-center bg-slate-900/40 dark:bg-black/60 backdrop-blur-sm p-4 animate-in fade-in duration-200">
                    <div className="bg-white dark:bg-[#0a0f18] rounded-3xl shadow-2xl w-full max-w-sm overflow-hidden border border-slate-200 dark:border-slate-800 p-10 flex flex-col items-center text-center animate-in zoom-in-95 duration-200">
                        <div className="w-20 h-20 rounded-full bg-red-100 dark:bg-red-600/10 text-red-500 flex items-center justify-center mb-8 border border-red-200 dark:border-red-500/20">
                            <span className="material-symbols-outlined text-[40px]">logout</span>
                        </div>
                        <h3 className="text-2xl font-black tracking-tight text-slate-900 dark:text-white mb-2">Ready to Leave?</h3>
                        <p className="text-slate-600 dark:text-slate-400 text-sm mb-10 leading-relaxed">
                            Are you sure you want to log out of your session? All unsaved work will be lost.
                        </p>
                        <div className="flex gap-4 w-full">
                            <button
                                onClick={() => setShowLogoutConfirm(false)}
                                className="flex-1 px-6 py-4 rounded-xl border border-slate-300 dark:border-slate-800 text-slate-600 dark:text-slate-400 font-bold uppercase tracking-widest text-[11px] hover:text-slate-900 dark:hover:text-white hover:bg-slate-50 dark:hover:bg-slate-800 transition-all cursor-pointer"
                            >
                                Stay
                            </button>
                            <button
                                onClick={onLogout}
                                className="flex-1 px-6 py-4 rounded-xl bg-red-600 hover:bg-red-700 text-white font-bold uppercase tracking-widest text-[11px] transition-all cursor-pointer shadow-xl shadow-red-600/20"
                            >
                                Logout
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

export default Layout;
