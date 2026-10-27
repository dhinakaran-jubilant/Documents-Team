import React, { useState, useEffect } from 'react';

const Layout = ({ children, user, onLogout, onTabChange, onTabClick, activeTab = 'fin-report', breadcrumbs = [] }) => {
    const [showLogoutConfirm, setShowLogoutConfirm] = useState(false);
    const defaultBreadcrumbs = {
        'fin-report': [
            { label: 'Home', icon: 'home', onClick: () => { onTabChange && onTabChange('fin-report'); onTabClick && onTabClick('fin-report'); } },
            { label: 'Fin Report' }
        ],
        'documat': [
            { label: 'Home', icon: 'home', onClick: () => { onTabChange && onTabChange('fin-report'); onTabClick && onTabClick('fin-report'); } },
            { label: 'Documat' }
        ],
        'history': [
            { label: 'Home', icon: 'home', onClick: () => { onTabChange && onTabChange('fin-report'); onTabClick && onTabClick('fin-report'); } },
            { label: 'History' }
        ],
        'users': [
            { label: 'Home', icon: 'home', onClick: () => { onTabChange && onTabChange('fin-report'); onTabClick && onTabClick('fin-report'); } },
            { label: 'Users' }
        ],
    };

    const currentBreadcrumbs = (breadcrumbs && breadcrumbs.length > 0)
        ? breadcrumbs
        : (defaultBreadcrumbs[activeTab] || [
            { label: 'Home', icon: 'home', onClick: () => { onTabChange && onTabChange('fin-report'); onTabClick && onTabClick('fin-report'); } }
        ]);

    const initials = user?.name ? user.name.split(' ').map(n => n[0]).join('').toUpperCase() : 'JD';

    return (
        <div className="relative flex h-screen w-full overflow-hidden bg-[#efefef] text-slate-800 font-[Inter]">
            {/* Full-Height Left Sidebar */}
            <aside className="w-[260px] border-r border-slate-200 bg-white flex flex-col shrink-0 h-screen">
                {/* Brand Section */}
                <div className="flex h-[64px] items-center px-6 border-b border-slate-200 shrink-0">
                    <h2 className="text-xl font-black tracking-wide bg-gradient-to-r from-[#d4a017] via-[#ab7d00] to-[#755500] text-transparent bg-clip-text whitespace-nowrap">JUBILANT GROUP</h2>
                </div>

                {/* Navigation Menu */}
                <div className="flex flex-col gap-2 p-4 flex-1 overflow-y-auto">
                    {(user?.role === 'admin' || !user?.accessed_menus || user.accessed_menus.includes('fin-report')) && (
                        <div
                            onClick={() => {
                                onTabChange && onTabChange('fin-report');
                                onTabClick && onTabClick('fin-report');
                            }}
                            className={`flex items-center gap-3 px-6 h-10 rounded-xl transition-all cursor-pointer ${activeTab === 'fin-report'
                                ? 'bg-[#ab7d00] text-white shadow-lg shadow-[#ab7d00]/25'
                                : 'bg-slate-100/60 text-slate-600 hover:text-[#ab7d00] hover:bg-slate-100'}`}
                        >
                            <span className="material-symbols-outlined" style={{fontSize: '16px'}}>table_view</span>
                            <span className="text-[12px] font-black uppercase tracking-[0.2em]">Fin Report</span>
                        </div>
                    )}

                    {(user?.role === 'admin' || !user?.accessed_menus || user.accessed_menus.includes('documat')) && (
                        <div
                            onClick={() => {
                                onTabChange && onTabChange('documat');
                                onTabClick && onTabClick('documat');
                            }}
                            className={`flex items-center gap-3 px-6 h-10 rounded-xl transition-all cursor-pointer ${activeTab === 'documat'
                                ? 'bg-[#ab7d00] text-white shadow-lg shadow-[#ab7d00]/25'
                                : 'bg-slate-200 text-slate-600 hover:text-[#ab7d00] hover:bg-slate-100'}`}
                        >
                            <span className="material-symbols-outlined" style={{fontSize: '16px'}}>description</span>
                            <span className="text-[12px] font-black uppercase tracking-[0.2em]">Documat</span>
                        </div>
                    )}

                    <div
                        onClick={() => {
                            onTabChange && onTabChange('history');
                            onTabClick && onTabClick('history');
                        }}
                        className={`flex items-center gap-3 px-6 h-10 rounded-xl transition-all cursor-pointer ${activeTab === 'history'
                            ? 'bg-[#ab7d00] text-white shadow-lg shadow-[#ab7d00]/25'
                            : 'bg-slate-200 text-slate-600 hover:text-[#ab7d00] hover:bg-slate-100'}`}
                    >
                        <span className="material-symbols-outlined" style={{fontSize: '16px'}}>history</span>
                        <span className="text-[12px] font-black uppercase tracking-[0.2em]">History</span>
                    </div>

                    {user?.role === 'admin' && (
                        <div
                            onClick={() => {
                                onTabChange && onTabChange('users');
                                onTabClick && onTabClick('users');
                            }}
                            className={`flex items-center gap-3 px-6 h-10 rounded-xl transition-all cursor-pointer ${activeTab === 'users'
                                ? 'bg-[#ab7d00] text-white shadow-lg shadow-[#ab7d00]/25'
                                : 'bg-slate-200 text-slate-600 hover:text-[#ab7d00] hover:bg-slate-100'}`}
                        >
                            <span className="material-symbols-outlined" style={{fontSize: '16px'}}>group</span>
                            <span className="text-[12px] font-black uppercase tracking-[0.2em]">Users</span>
                        </div>
                    )}
                </div>

                {/* User Profile Footer */}
                <div className="mt-auto p-4 border-t border-slate-200 bg-white shrink-0">
                    <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-full bg-[#ab7d00] flex items-center justify-center text-white font-bold text-xs ring-4 ring-[#ab7d00]/15 shrink-0">
                            {initials}
                        </div>
                        <div className="flex-1 overflow-hidden">
                            <p className="text-slate-900 text-[14px] font-bold truncate" title={user?.name}>{user?.name || 'User'}</p>
                            <p className="text-[10px] text-slate-500 font-bold uppercase tracking-widest truncate">{user?.role || 'Staff'}</p>
                        </div>
                        <button
                            onClick={() => setShowLogoutConfirm(true)}
                            className="text-slate-400 hover:text-red-600 transition-colors cursor-pointer p-1"
                            title="Logout"
                        >
                            <span className="material-symbols-outlined text-lg">logout</span>
                        </button>
                    </div>
                </div>
            </aside>

            {/* Right Main Content Area */}
            <main className="flex-1 flex flex-col h-screen relative overflow-hidden bg-[#efefef]">
                {/* Breadcrumb Navigation Bar */}
                <div className="px-10 pt-6 pb-2 shrink-0">
                    <nav aria-label="Breadcrumb" className="flex items-center gap-2 text-[13px] font-medium text-slate-500">
                        {currentBreadcrumbs.map((crumb, idx) => {
                            const isLast = idx === currentBreadcrumbs.length - 1;
                            return (
                                <React.Fragment key={idx}>
                                    {crumb.onClick && !isLast ? (
                                        <button
                                            type="button"
                                            onClick={crumb.onClick}
                                            className="hover:text-[#ab7d00] transition-colors cursor-pointer flex items-center gap-1.5 focus:outline-none"
                                        >
                                            <span>{crumb.label}</span>
                                        </button>
                                    ) : (
                                        <span className={`flex items-center gap-1.5 ${isLast ? 'text-[#ab7d00] font-bold' : ''}`}>
                                            {crumb.icon && (
                                                <span className="material-symbols-outlined text-[17px]">{crumb.icon}</span>
                                            )}
                                            <span>{crumb.label}</span>
                                        </span>
                                    )}
                                    {!isLast && (
                                        <span className="material-symbols-outlined text-[15px] text-slate-400 select-none">
                                            chevron_right
                                        </span>
                                    )}
                                </React.Fragment>
                            );
                        })}
                    </nav>
                </div>

                <div className={`flex-1 relative ${activeTab === 'users' ? 'overflow-hidden flex flex-col' : 'overflow-y-auto scrollbar-slim'}`}>
                    {children}
                </div>
            </main>

            {/* Logout Confirmation Modal */}
            {showLogoutConfirm && (
                <div className="fixed inset-0 z-[150] flex items-center justify-center bg-slate-900/40 backdrop-blur-sm p-4 animate-in fade-in duration-200">
                    <div className="bg-white rounded-3xl shadow-2xl w-full max-w-sm overflow-hidden border border-slate-200 p-10 flex flex-col items-center text-center animate-in zoom-in-95 duration-200">
                        <div className="w-20 h-20 rounded-full bg-red-100 text-red-500 flex items-center justify-center mb-8 border border-red-200">
                            <span className="material-symbols-outlined text-[40px]">logout</span>
                        </div>
                        <h3 className="text-2xl font-black tracking-tight text-slate-900 mb-2">Ready to Leave?</h3>
                        <p className="text-slate-600 text-sm mb-10 leading-relaxed">
                            Are you sure you want to log out of your session? All unsaved work will be lost.
                        </p>
                        <div className="flex gap-4 w-full">
                            <button
                                onClick={() => setShowLogoutConfirm(false)}
                                className="flex-1 px-6 py-4 rounded-xl border border-slate-300 text-slate-600 font-bold uppercase tracking-widest text-[11px] hover:text-slate-900 hover:bg-slate-50 transition-all cursor-pointer"
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
