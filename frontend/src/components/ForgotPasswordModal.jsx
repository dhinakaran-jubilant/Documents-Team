/**
 * Project: Fin Report - Documents team
 * Author: Dhinakaran Sekar
 * Email: dhinakaran.s@jubilantenterprises.in
 * Date: 2026-04-30 18:41
 * Description: Modal component for recovering a forgotten password using security questions.
 */

import React, { useState } from 'react';
import SuccessModal from './SuccessModal';
import config from './config';

/**
 * ForgotPasswordModal component.
 * @param {Object} props - Component props.
 * @param {Function} props.onClose - Callback function to close the modal.
 */
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

  /**
   * Fetches the security question for the provided employee code.
   */
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

  /**
   * Transitions to the password reset step after user provides an answer.
   */
  const handleVerifyAnswer = (e) => {
    e.preventDefault();
    if (!answer) {
      setError('Answer is required.');
      return;
    }
    setStep(3);
  };

  /**
   * Resets the user's password after verifying the security answer.
   */
  const handleResetPassword = async (e) => {
    e.preventDefault();
    setError('');
    // Admins don't need confirm password validation
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
      <div className="w-full max-w-md bg-white/90 backdrop-blur-xl rounded-2xl shadow-2xl border border-white/20 overflow-hidden animate-in fade-in zoom-in-95 duration-300">
        <div className="p-10">
          <div className="flex justify-between items-center mb-8">
            <h2 className="text-2xl font-black text-slate-900 mb-2 tracking-tight">Access Recovery</h2>
            <button onClick={onClose} className="text-slate-400 hover:text-slate-600 transition-colors cursor-pointer">
              <span className="material-symbols-outlined">close</span>
            </button>
          </div>

          {/* Stepper UI */}
          <div className="flex items-center justify-center gap-3 mb-10 w-full">
            {[1, 2, 3].map((s) => (
              <React.Fragment key={s}>
                <div className="flex items-center justify-center shrink-0">
                  <div className={`w-10 h-10 rounded-2xl flex items-center justify-center text-sm font-black text-center leading-none transition-all ${step >= s ? 'bg-blue-600 text-white shadow-lg shadow-blue-600/20' : 'bg-slate-300 text-slate-700'}`}>
                    {s}
                  </div>
                </div>
                {s < 3 && (
                  <div className={`w-12 h-1.5 rounded-full transition-all shrink-0 ${step > s ? 'bg-blue-600' : 'bg-slate-300'}`} />
                )}
              </React.Fragment>
            ))}
          </div>

          <form onSubmit={step === 1 ? handleFetchQuestion : step === 2 ? handleVerifyAnswer : handleResetPassword} className="space-y-8">
            {step === 1 && (
              <div className="space-y-4">
                <p className="text-xs font-bold text-slate-500 uppercase tracking-wider">Step 1: Identify</p>
                <div className="space-y-2">
                  <label className="text-[10px] font-black text-slate-700 uppercase tracking-[0.2em] ml-1">Employee Code <span className="text-rose-500">*</span></label>
                  <input
                    type="text"
                    value={employeeCode}
                    onChange={(e) => setEmployeeCode(e.target.value)}
                    placeholder="EX: E001"
                    className="w-full h-14 px-5 rounded-2xl border border-slate-200 bg-white placeholder:text-slate-400 text-slate-900 text-sm font-medium focus:ring-4 focus:ring-blue-600/5 focus:border-blue-600 focus:outline-none transition-all"
                    required
                  />
                </div>
              </div>
            )}

            {step === 2 && (
              <div className="space-y-4">
                <div className="p-6 rounded-[2rem] bg-blue-200/80 border border-blue-100/80">
                  <label className="text-[10px] font-black text-blue-600 uppercase tracking-[0.2em] block mb-2">Security Question</label>
                  <p className="text-slate-900 font-bold">{question}</p>
                </div>
                <div className="space-y-2">
                  <label className="text-[10px] font-black text-slate-700 uppercase tracking-[0.2em] ml-1">Your Answer <span className="text-rose-500">*</span></label>
                  <div className="relative">
                    <input
                      type={showAnswer ? 'text' : 'password'}
                      value={answer}
                      onChange={(e) => setAnswer(e.target.value)}
                      placeholder="Enter your security answer"
                      className="w-full h-14 px-5 rounded-2xl border border-slate-200 bg-white placeholder:text-slate-400 text-slate-900 text-sm font-medium focus:ring-4 focus:ring-blue-600/5 focus:border-blue-600 focus:outline-none transition-all"
                      required
                    />
                    <button
                      type="button"
                      onClick={() => setShowAnswer(prev => !prev)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 w-10 h-10 flex items-center justify-center rounded-xl hover:bg-slate-100 transition-colors z-10 cursor-pointer"
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
                    <label className="text-[10px] font-black text-slate-700 uppercase tracking-[0.2em] ml-1">New Password <span className="text-rose-500">*</span></label>
                    <div className="relative">
                      <input
                        type={showNewPassword ? 'text' : 'password'}
                        value={newPassword}
                        onChange={(e) => setNewPassword(e.target.value)}
                        placeholder="••••••••"
                        className="w-full h-14 px-5 rounded-2xl border border-slate-200 bg-white placeholder:text-slate-400 text-slate-900 text-sm font-medium focus:ring-4 focus:ring-blue-600/5 focus:border-blue-600 focus:outline-none transition-all"
                        required
                      />
                      <button
                        type="button"
                        onClick={() => setShowNewPassword((prev) => !prev)}
                        className="absolute right-3 top-1/2 -translate-y-1/2 w-10 h-10 flex items-center justify-center rounded-xl hover:bg-slate-100 transition-colors z-10 cursor-pointer"
                      >
                        <span className="material-symbols-outlined text-slate-400 text-lg select-none">
                          {showNewPassword ? 'visibility_off' : 'visibility'}
                        </span>
                      </button>
                    </div>
                  </div>
                  {userRole !== 'admin' && (
                    <div className="space-y-2">
                      <label className="text-[10px] font-black text-slate-700 uppercase tracking-[0.2em] ml-1">Confirm Password <span className="text-rose-500">*</span></label>
                      <div className="relative">
                        <input
                          type={showConfirmPassword ? 'text' : 'password'}
                          value={confirmPassword}
                          onChange={(e) => setConfirmPassword(e.target.value)}
                          placeholder="••••••••"
                          className="w-full h-14 px-5 rounded-2xl border border-slate-200 bg-white placeholder:text-slate-400 text-slate-900 text-sm font-medium focus:ring-4 focus:ring-blue-600/5 focus:border-blue-600 focus:outline-none transition-all"
                          required
                        />
                        <button
                          type="button"
                          onClick={() => setShowConfirmPassword((prev) => !prev)}
                          className="absolute right-3 top-1/2 -translate-y-1/2 w-10 h-10 flex items-center justify-center rounded-xl hover:bg-slate-100 transition-colors z-10 cursor-pointer"
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
              <div className="p-4 rounded-2xl bg-red-50 text-red-500 text-[11px] font-bold border border-red-100 text-center animate-in shake duration-300">
                {error}
              </div>
            )}

            <div className="flex gap-4">
              {step > 1 && (
                <button
                  type="button"
                  onClick={() => setStep(step - 1)}
                  className="flex-1 h-14 rounded-2xl border-2 border-slate-200 text-slate-500 font-black text-xs uppercase tracking-widest hover:bg-slate-50 hover:border-slate-300 transition-all active:scale-95 cursor-pointer"
                >
                  Back
                </button>
              )}
              <button
                type="submit"
                disabled={loading}
                className="flex-[2] bg-slate-900 text-white font-black h-14 rounded-2xl transition-all shadow-xl shadow-slate-900/10 flex items-center justify-center gap-2 group disabled:opacity-70 disabled:cursor-not-allowed uppercase tracking-[0.2em] text-xs active:scale-95 cursor-pointer"
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
