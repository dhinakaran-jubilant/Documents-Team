/**
 * Project: Documents Team
 * Component: SuccessModal
 * Author: Dhinakaran Sekar
 * Email: dhinakaran.s@jubilantenterprises.in
 * Date: 2026-04-22 13:00:00
 */
import React from 'react';

export default function SuccessModal({ title, message, onClose }) {
  return (
    <div className="fixed inset-0 z-[200] flex items-center justify-center bg-slate-900/60 backdrop-blur-md p-4">
      <div className="w-full max-w-sm bg-white/90 dark:bg-slate-900/90 backdrop-blur-xl rounded-[2.5rem] shadow-2xl border border-white/20 overflow-hidden animate-in fade-in zoom-in-95 duration-300">
        <div className="p-10 text-center">
          <div className="w-20 h-20 bg-emerald-500/10 rounded-full flex items-center justify-center mx-auto mb-6">
            <span className="material-symbols-outlined text-emerald-500 text-4xl">check_circle</span>
          </div>
          <h2 className="text-2xl font-black text-slate-900 dark:text-white mb-2 uppercase tracking-tight">{title}</h2>
          <p className="text-slate-500 dark:text-slate-400 text-sm font-medium leading-relaxed mb-8">
            {message}
          </p>
          <button
            onClick={onClose}
            className="w-full bg-slate-900 dark:bg-white text-white dark:text-slate-900 font-black h-14 rounded-2xl transition-all shadow-xl shadow-slate-900/10 dark:shadow-white/10 flex items-center justify-center gap-2 group uppercase tracking-widest text-xs"
          >
            CONTINUE TO LOGIN
            <span className="material-symbols-outlined text-lg group-hover:translate-x-1 transition-transform">east</span>
          </button>
        </div>
      </div>
    </div>
  );
}
