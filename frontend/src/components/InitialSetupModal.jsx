/**
 * Project: Documents Team
 * Component: InitialSetupModal
 * Author: Dhinakaran Sekar
 * Email: dhinakaran.s@jubilantenterprises.in
 * Date: 2026-04-22 13:00:00
 */
import React, { useState } from 'react';
import SuccessModal from './SuccessModal';
import config from './config';

export default function InitialSetupModal({ employeeCode, userRole, onClose }) {
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showNewPassword, setShowNewPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [q1, setQ1] = useState('');
  const [a1, setA1] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [showSuccess, setShowSuccess] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');

    if (userRole !== 'admin' && newPassword !== confirmPassword) {
      setError('Passwords do not match.');
      return;
    }

    if (newPassword.length < 6) {
      setError('Password must be at least 6 characters.');
      return;
    }

    if (!q1 || !a1) {
      setError('Please provide a security question and answer.');
      return;
    }

    setLoading(true);
    try {
      const response = await fetch(`${config.API_BASE_URL}/api/users/initial-setup/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          employee_code: employeeCode,
          new_password: newPassword,
          q1,
          a1
        }),
      });

      const data = await response.json();
      if (data.success) {
        setShowSuccess(true);
      } else {
        setError(data.message || 'Setup failed.');
      }
    } catch (err) {
      setError('An error occurred. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  if (showSuccess) {
    return (
      <SuccessModal 
        title="Account Secured!" 
        message="Your password and security question have been updated. You can now login to the system." 
        onClose={onClose} 
      />
    );
  }

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-slate-900/60 backdrop-blur-md p-4">
      <div className="w-full max-w-md bg-white/90 dark:bg-slate-900/90 backdrop-blur-xl rounded-2xl shadow-2xl border border-white/20 overflow-hidden animate-in fade-in zoom-in-95 duration-300">
        <div className="p-10">
          <div className="flex justify-between items-center mb-8">
            <div>
              <h2 className="text-3xl font-black text-slate-900 dark:text-slate-100">Confirm  Password</h2>
              <p className="text-slate-500 dark:text-slate-400 text-xs mt-2 font-bold uppercase tracking-wider">Set your permanent credentials</p>
            </div>
          </div>

          <form onSubmit={handleSubmit} className="space-y-6">
            <div className="flex flex-col gap-6">
              {/* Password Section */}
              <div className="space-y-4">
                <div className="space-y-2">
                  <label className="text-[12px] font-black text-slate-700 dark:text-slate-300 uppercase tracking-[0.1em] ml-1">New Password <span className="text-rose-500">*</span></label>
                  <div className="relative">
                    <input
                      type={showNewPassword ? 'text' : 'password'}
                      value={newPassword}
                      onChange={(e) => setNewPassword(e.target.value)}
                      placeholder="••••••••"
                      className="w-full h-12 px-4 rounded-2xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800/50 text-sm font-medium dark:text-white focus:ring-4 focus:ring-primary/10 focus:border-primary focus:outline-none transition-all"
                      required
                    />
                    <button
                      type="button"
                      onClick={() => setShowNewPassword((prev) => !prev)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 w-8 h-8 flex items-center justify-center rounded-xl hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors z-10"
                    >
                      <span className="material-symbols-outlined text-slate-400 text-lg select-none">
                        {showNewPassword ? 'visibility_off' : 'visibility'}
                      </span>
                    </button>
                  </div>
                </div>
                {userRole !== 'admin' && (
                  <div className="space-y-2">
                    <label className="text-[12px] font-black text-slate-700 dark:text-slate-300 uppercase tracking-[0.1em] ml-1">Confirm Password <span className="text-rose-500">*</span></label>
                    <div className="relative">
                      <input
                        type={showConfirmPassword ? 'text' : 'password'}
                        value={confirmPassword}
                        onChange={(e) => setConfirmPassword(e.target.value)}
                        placeholder="••••••••"
                        className="w-full h-12 px-4 rounded-2xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800/50 text-sm font-medium dark:text-white focus:ring-4 focus:ring-primary/10 focus:border-primary focus:outline-none transition-all"
                        required
                      />
                      <button
                        type="button"
                        onClick={() => setShowConfirmPassword((prev) => !prev)}
                        className="absolute right-3 top-1/2 -translate-y-1/2 w-8 h-8 flex items-center justify-center rounded-xl hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors z-10"
                      >
                        <span className="material-symbols-outlined text-slate-400 text-lg select-none">
                          {showConfirmPassword ? 'visibility_off' : 'visibility'}
                        </span>
                      </button>
                    </div>
                  </div>
                )}
              </div>

              {/* Security Questions Section */}
              <div className="space-y-4 pt-6 border-t border-slate-100 dark:border-slate-800">
                <div className="space-y-2">
                  <label className="text-[12px] font-black text-slate-700 dark:text-slate-300 uppercase tracking-[0.1em] ml-1">Security Question <span className="text-rose-500">*</span></label>
                  <select
                    value={q1}
                    onChange={(e) => setQ1(e.target.value)}
                    className="w-full h-12 px-4 rounded-2xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800/50 text-sm font-medium dark:text-white focus:ring-4 focus:ring-primary/10 focus:border-primary focus:outline-none transition-all"
                    required
                  >
                    <option value="">Select a question</option>
                    <option value="What is your mother's maiden name?">What is your mother's maiden name?</option>
                    <option value="What was the name of your first pet?">What was the name of your first pet?</option>
                    <option value="What city were you born in?">What city were you born in?</option>
                    <option value="What was the name of your elementary school?">What was the name of your elementary school?</option>
                  </select>
                </div>
                <div className="space-y-2">
                  <label className="text-[12px] font-black text-slate-700 dark:text-slate-300 uppercase tracking-[0.1em] ml-1">Your Secret Answer <span className="text-rose-500">*</span></label>
                  <input
                    type="text"
                    value={a1}
                    onChange={(e) => setA1(e.target.value)}
                    placeholder="Recovery answer"
                    className="w-full h-12 px-4 rounded-2xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800/50 text-sm font-medium dark:text-white focus:ring-4 focus:ring-primary/10 focus:border-primary focus:outline-none transition-all"
                    required
                  />
                </div>
              </div>
            </div>

            {error && (
              <div className="p-4 rounded-2xl bg-red-50 dark:bg-red-900/20 text-red-500 text-[11px] font-bold border border-red-100 dark:border-red-900/30 flex items-center gap-2">
                <span className="material-symbols-outlined text-lg">error</span>
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full bg-slate-900 dark:bg-white text-white dark:text-slate-900 font-black h-14 rounded-2xl transition-all shadow-xl shadow-slate-900/10 dark:shadow-white/10 flex items-center justify-center gap-2 group disabled:opacity-70 disabled:cursor-not-allowed uppercase tracking-widest text-sm"
            >
              {loading ? (
                'Processing...'
              ) : (
                <>
                  Complete Setup
                  <span className="material-symbols-outlined text-lg group-hover:translate-x-1 transition-transform">check_circle</span>
                </>
              )}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
