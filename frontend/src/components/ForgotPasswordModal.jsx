/**
 * Project: Documents Team
 * Component: ForgotPasswordModal
 * Author: Dhinakaran Sekar
 * Email: dhinakaran.s@jubilantenterprises.in
 * Date: 2026-04-22 13:00:00
 */
import React, { useState } from 'react';
import SuccessModal from './SuccessModal';
import config from './config';

export default function ForgotPasswordModal({ onClose }) {
  const [step, setStep] = useState(1); // 1: Employee Code, 2: Security Question, 3: New Password
  const [employeeCode, setEmployeeCode] = useState('');
  const [question, setQuestion] = useState('');
  const [answer, setAnswer] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showAnswer, setShowAnswer] = useState(false);
  const [showNewPassword, setShowNewPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [userRole, setUserRole] = useState('');
  const [showSuccess, setShowSuccess] = useState(false);

  const handleFetchQuestion = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const response = await fetch(`${config.API_BASE_URL}/api/forgot-password/request/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ employee_code: employeeCode }),
      });
      const data = await response.json();
      if (data.success) {
        setQuestion(data.question);
        setUserRole(data.role);
        setStep(2);
      } else {
        setError(data.message || 'Employee Code not found.');
      }
    } catch (err) {
      setError('An error occurred. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleVerifyAnswer = (e) => {
    e.preventDefault();
    if (!answer) {
      setError('Answer is required.');
      return;
    }
    setStep(3);
  };

  const handleResetPassword = async (e) => {
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

    setLoading(true);
    try {
      const response = await fetch(`${config.API_BASE_URL}/api/forgot-password/reset/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          employee_code: employeeCode, 
          answer: answer, 
          new_password: newPassword 
        }),
      });
      const data = await response.json();
      if (data.success) {
        setShowSuccess(true);
      } else {
        setError(data.message || 'Verification failed.');
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
        title="Access Restored!" 
        message="Your password has been updated successfully. You can now login with your new credentials." 
        onClose={onClose} 
      />
    );
  }

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-slate-900/60 backdrop-blur-md p-4">
      <div className="w-full max-w-md bg-white/90 dark:bg-slate-900/90 backdrop-blur-xl rounded-2xl shadow-2xl border border-white/20 overflow-hidden animate-in fade-in zoom-in-95 duration-300">
        <div className="p-10">
          <div className="flex justify-between items-center mb-8">
            <h2 className="text-2xl font-black text-slate-900 dark:text-white mb-2 tracking-tight">Access Recovery</h2>
            <button onClick={onClose} className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 transition-colors">
              <span className="material-symbols-outlined">close</span>
            </button>
          </div>

          {/* Stepper UI */}
          <div className="flex items-center gap-2 mb-10">
            {[1, 2, 3].map((s) => (
              <div key={s} className="flex-1 flex items-center gap-2">
                <div className={`w-10 h-10 rounded-2xl flex items-center justify-center text-xs font-black transition-all ${step >= s ? 'bg-primary text-white shadow-lg shadow-primary/20' : 'bg-slate-100 text-slate-400 dark:bg-slate-800'}`}>
                  {s}
                </div>
                {s < 3 && <div className={`flex-1 h-1.5 rounded-full transition-all ${step > s ? 'bg-primary' : 'bg-slate-100 dark:bg-slate-800'}`} />}
              </div>
            ))}
          </div>

          <form onSubmit={step === 1 ? handleFetchQuestion : step === 2 ? handleVerifyAnswer : handleResetPassword} className="space-y-8">
            {step === 1 && (
              <div className="space-y-4">
                <p className="text-xs font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider">Step 1: Identify</p>
                <div className="space-y-2">
                  <label className="text-[10px] font-black text-slate-700 dark:text-slate-300 uppercase tracking-[0.2em] ml-1">Employee Code <span className="text-rose-500">*</span></label>
                  <input
                    type="text"
                    value={employeeCode}
                    onChange={(e) => setEmployeeCode(e.target.value)}
                    placeholder="EX: E001"
                    className="w-full h-14 px-5 rounded-2xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800/50 text-sm font-medium dark:text-white focus:ring-4 focus:ring-primary/10 focus:border-primary focus:outline-none transition-all"
                    required
                  />
                </div>
              </div>
            )}

            {step === 2 && (
              <div className="space-y-4">
                <div className="p-6 rounded-[2rem] bg-primary/5 border border-primary/10">
                  <label className="text-[10px] font-black text-primary uppercase tracking-[0.2em] block mb-2">Security Question</label>
                  <p className="text-slate-900 dark:text-slate-100 font-bold">{question}</p>
                </div>
                <div className="space-y-2">
                  <label className="text-[10px] font-black text-slate-700 dark:text-slate-300 uppercase tracking-[0.2em] ml-1">Your Answer <span className="text-rose-500">*</span></label>
                  <div className="relative">
                    <input
                      type={showAnswer ? 'text' : 'password'}
                      value={answer}
                      onChange={(e) => setAnswer(e.target.value)}
                      placeholder="Enter your security answer"
                      className="w-full h-14 px-5 rounded-2xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800/50 text-sm font-medium dark:text-white focus:ring-4 focus:ring-primary/10 focus:border-primary focus:outline-none transition-all"
                      required
                    />
                    <button
                      type="button"
                      onClick={() => setShowAnswer(prev => !prev)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 w-10 h-10 flex items-center justify-center rounded-xl hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors z-10"
                    >
                      <span className="material-symbols-outlined text-slate-400 text-lg select-none">
                        {showAnswer ? 'visibility_off' : 'visibility'}
                      </span>
                    </button>
                  </div>
                </div>
              </div>
            )}

            {step === 3 && (
              <div className="space-y-4">
                <p className="text-[10px] font-black text-emerald-500 uppercase tracking-[0.2em] ml-1">Step 3: Reset</p>
                <div className="space-y-4">
                  <div className="space-y-2">
                    <label className="text-[10px] font-black text-slate-700 dark:text-slate-300 uppercase tracking-[0.2em] ml-1">New Password <span className="text-rose-500">*</span></label>
                    <div className="relative">
                      <input
                        type={showNewPassword ? 'text' : 'password'}
                        value={newPassword}
                        onChange={(e) => setNewPassword(e.target.value)}
                        placeholder="••••••••"
                        className="w-full h-14 px-5 rounded-2xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800/50 text-sm font-medium dark:text-white focus:ring-4 focus:ring-primary/10 focus:border-primary focus:outline-none transition-all"
                        required
                      />
                      <button
                        type="button"
                        onClick={() => setShowNewPassword((prev) => !prev)}
                        className="absolute right-3 top-1/2 -translate-y-1/2 w-10 h-10 flex items-center justify-center rounded-xl hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors z-10"
                      >
                        <span className="material-symbols-outlined text-slate-400 text-lg select-none">
                          {showNewPassword ? 'visibility_off' : 'visibility'}
                        </span>
                      </button>
                    </div>
                  </div>
                  {userRole !== 'admin' && (
                    <div className="space-y-2">
                      <label className="text-[10px] font-black text-slate-700 dark:text-slate-300 uppercase tracking-[0.2em] ml-1">Confirm Password <span className="text-rose-500">*</span></label>
                      <div className="relative">
                        <input
                          type={showConfirmPassword ? 'text' : 'password'}
                          value={confirmPassword}
                          onChange={(e) => setConfirmPassword(e.target.value)}
                          placeholder="••••••••"
                          className="w-full h-14 px-5 rounded-2xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800/50 text-sm font-medium dark:text-white focus:ring-4 focus:ring-primary/10 focus:border-primary focus:outline-none transition-all"
                          required
                        />
                        <button
                          type="button"
                          onClick={() => setShowConfirmPassword((prev) => !prev)}
                          className="absolute right-3 top-1/2 -translate-y-1/2 w-10 h-10 flex items-center justify-center rounded-xl hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors z-10"
                        >
                          <span className="material-symbols-outlined text-slate-400 text-lg select-none">
                            {showConfirmPassword ? 'visibility_off' : 'visibility'}
                          </span>
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            )}

            {error && (
              <div className="p-4 rounded-2xl bg-red-50 dark:bg-red-900/20 text-red-500 text-[11px] font-bold border border-red-100 dark:border-red-900/30 text-center animate-in shake duration-300">
                {error}
              </div>
            )}

            <div className="flex gap-4">
              {step > 1 && (
                <button
                  type="button"
                  onClick={() => setStep(step - 1)}
                  className="flex-1 h-14 rounded-2xl border-2 border-slate-100 dark:border-slate-800 text-slate-500 dark:text-slate-400 font-black text-xs uppercase tracking-widest hover:bg-slate-50 dark:hover:bg-slate-800 transition-all active:scale-95"
                >
                  Back
                </button>
              )}
              <button
                type="submit"
                disabled={loading}
                className="flex-[2] bg-slate-900 dark:bg-white text-white dark:text-slate-900 font-black h-14 rounded-2xl transition-all shadow-xl shadow-slate-900/10 dark:shadow-white/10 flex items-center justify-center gap-2 group disabled:opacity-70 disabled:cursor-not-allowed uppercase tracking-[0.2em] text-xs active:scale-95"
              >
                {loading ? 'Wait...' : step === 3 ? 'RESET' : 'NEXT'}
                {!loading && <span className="material-symbols-outlined text-sm group-hover:translate-x-1 transition-transform">east</span>}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}
