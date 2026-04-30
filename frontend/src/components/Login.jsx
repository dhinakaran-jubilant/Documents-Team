/**
 * Project: Documents Team
 * Component: Login
 * Author: Dhinakaran Sekar
 * Email: dhinakaran.s@jubilantenterprises.in
 * Date: 2026-04-22 13:00:00
 */
import React, { useState, useEffect } from 'react';
import InitialSetupModal from './InitialSetupModal';
import ForgotPasswordModal from './ForgotPasswordModal';
import config from './config';

export default function Login({ onLogin }) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [rememberMe, setRememberMe] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [showSetup, setShowSetup] = useState(false);
  const [showForgot, setShowForgot] = useState(false);
  const [tempUser, setTempUser] = useState(null);

  useEffect(() => {
    if (error) {
      const timer = setTimeout(() => {
        setError('');
      }, 5000);
      return () => clearTimeout(timer);
    }
  }, [error]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    
    try {
      const response = await fetch(`${config.API_BASE_URL}/api/login/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ employee_code: email, password }),
      });

      const data = await response.json();

      if (response.ok && data.success) {
        if (data.user.is_initial_password && data.user.role !== 'admin') {
          setTempUser(data.user);
          setShowSetup(true);
        } else {
          if (onLogin) onLogin(data.user);
        }
      } else {
        setError(data.message || 'Login failed. Please try again.');
      }
    } catch (err) {
      setError('An error occurred. Please try again later.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="relative flex min-h-screen w-full flex-col items-center justify-center p-6 bg-slate-50 font-[Inter] antialiased">
      {/* Centered Login Card */}
      <div className="w-full max-w-[440px] bg-white rounded-[1.5rem] shadow-[0_8px_30px_rgb(0,0,0,0.04)] border border-slate-100 overflow-hidden">
        <div className="p-8 sm:p-12">
          {/* Header */}
          <div className="mb-10 text-center">
            <h2 className="text-slate-900 text-2xl font-bold tracking-tight">Welcome back</h2>
            <p className="text-slate-500 mt-2 text-[13px]">
              Sign in to your account to continue
            </p>
          </div>

          <form className="space-y-6" onSubmit={handleSubmit}>
            {/* Email Field */}
            <div className="flex flex-col gap-2">
              <label className="text-slate-900 text-[13px] font-semibold ml-1">Employee Code</label>
              <div className="relative group">
                <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none text-slate-400 group-focus-within:text-blue-600 transition-colors">
                  <span className="material-symbols-outlined text-[20px]">badge</span>
                </div>
                <input
                  type="text"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="Enter your employee code"
                  required
                  className="flex w-full rounded-xl text-slate-900 border border-slate-200 bg-white h-12 pl-12 pr-4 placeholder:text-slate-400 focus:outline-none focus:ring-4 focus:ring-blue-600/5 focus:border-blue-600 transition-all text-sm font-medium"
                />
              </div>
            </div>

            {/* Password Field */}
            <div className="flex flex-col gap-2">
              <div className="flex justify-between items-center px-1">
                <label className="text-slate-900 text-[13px] font-semibold">Password</label>
                <button 
                  type="button"
                  onClick={() => setShowForgot(true)}
                  className="text-blue-600 text-[11px] font-bold hover:text-blue-700 transition-colors"
                >
                  Forgot Password?
                </button>
              </div>
              <div className="relative group">
                <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none text-slate-400 group-focus-within:text-blue-600 transition-colors">
                  <span className="material-symbols-outlined text-[20px]">lock</span>
                </div>
                <input
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  required
                  className="flex w-full rounded-xl text-slate-900 border border-slate-200 bg-white h-12 pl-12 pr-12 placeholder:text-slate-400 focus:outline-none focus:ring-4 focus:ring-blue-600/5 focus:border-blue-600 transition-all text-sm font-medium"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword((prev) => !prev)}
                  className="absolute inset-y-0 right-0 pr-4 flex items-center text-slate-400 hover:text-slate-600 transition-colors"
                >
                  <span className="material-symbols-outlined text-[20px]">
                    {showPassword ? 'visibility_off' : 'visibility'}
                  </span>
                </button>
              </div>
            </div>

            {/* Remember Me */}
            <div className="flex items-center gap-2.5 py-1 px-1">
              <input
                id="remember"
                type="checkbox"
                checked={rememberMe}
                onChange={(e) => setRememberMe(e.target.checked)}
                className="w-4 h-4 rounded border-slate-300 text-blue-600 focus:ring-blue-600/20 transition-all cursor-pointer shadow-sm"
              />
              <label htmlFor="remember" className="text-slate-600 text-[13px] font-medium cursor-pointer select-none">
                Remember this device
              </label>
            </div>

            {/* Sign In Button */}
            <button
              type="submit"
              disabled={loading}
              className={`w-full bg-blue-600 text-white font-bold h-12 rounded-xl transition-all shadow-lg shadow-blue-600/10 flex items-center justify-center gap-2 mt-4 active:scale-[0.98] ${loading ? 'opacity-70 cursor-not-allowed' : 'hover:bg-blue-700'}`}
            >
              {loading ? (
                <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              ) : (
                <>
                  Sign In
                  <span className="material-symbols-outlined text-[18px]">east</span>
                </>
              )}
            </button>
            
            {/* Error Message */}
            {error && (
              <div className="text-red-600 text-[12px] font-medium mt-4 text-center bg-red-50 p-3 rounded-xl border border-red-100 animate-in fade-in slide-in-from-top-2 duration-300">
                {error}
              </div>
            )}
          </form>
        </div>
      </div>

      {/* Setup Modal */}
      {showSetup && (
        <InitialSetupModal 
          employeeCode={tempUser.employee_code} 
          userRole={tempUser.role}
          onClose={() => {
            setShowSetup(false);
            if (onLogin) onLogin({ ...tempUser, is_initial_password: false });
          }} 
        />
      )}

      {/* Forgot Password Modal */}
      {showForgot && (
        <ForgotPasswordModal onClose={() => setShowForgot(false)} />
      )}
    </div>
  );
}

