/**
 * Project: Fin Report - Documents team
 * Author: Dhinakaran Sekar
 * Email: dhinakaran.s@jubilantenterprises.in
 * Date: 2026-04-30 18:41
 * Description: Main Application component that handles user session management and auto-logout logic.
 */

import React, { useState, useEffect } from 'react';
import Upload from './components/Upload';
import Documat from './components/Documat';
import Login from './components/Login';
import Users from './components/Users';
import History from './components/History';

/**
 * Main App component.
 * Manages the authenticated user state and implements an inactivity timeout.
 */
function App() {
  const [user, setUser] = useState(() => {
    const savedUser = localStorage.getItem('user');
    return savedUser ? JSON.parse(savedUser) : null;
  });

  const [activeTab, setActiveTab] = useState('fin-report');
  
  // Sync document theme: forces light mode on Login screen, applies dark/light on dashboard
  useEffect(() => {
    if (user) {
      const isDark = localStorage.getItem('isDark') !== 'false';
      if (isDark) {
        document.documentElement.classList.add('dark');
      } else {
        document.documentElement.classList.remove('dark');
      }
    } else {
      document.documentElement.classList.remove('dark');
    }
  }, [user]);

  // Sync user state with localStorage
  useEffect(() => {
    if (user) {
      localStorage.setItem('user', JSON.stringify(user));
    } else {
      localStorage.removeItem('user');
    }
  }, [user]);

  /**
   * Logs out the current user by clearing the user state.
   */
  const handleLogout = () => {
    setUser(null);
  };

  /**
   * Implements auto-logout after 1 hour of inactivity.
   * Tracks various user interaction events to reset the timer.
   */
  useEffect(() => {
    if (!user) return;

    let logoutTimer;
    const timeoutDuration = 60 * 60 * 1000; // 1 hour

    const resetTimer = () => {
      if (logoutTimer) clearTimeout(logoutTimer);
      logoutTimer = setTimeout(() => {
        handleLogout();
      }, timeoutDuration);
    };

    // Track user activity
    const activityEvents = ['mousedown', 'mousemove', 'keydown', 'scroll', 'touchstart', 'click'];
    
    activityEvents.forEach(event => {
      window.addEventListener(event, resetTimer);
    });

    // Initialize timer
    resetTimer();

    return () => {
      if (logoutTimer) clearTimeout(logoutTimer);
      activityEvents.forEach(event => {
        window.removeEventListener(event, resetTimer);
      });
    };
  }, [user]);

  if (!user) {
    return <Login onLogin={setUser} />;
  }

  if (activeTab === 'documat') {
    return <Documat user={user} onLogout={handleLogout} onTabChange={setActiveTab} />;
  }

  if (activeTab === 'users') {
    return <Users user={user} onLogout={handleLogout} onTabChange={setActiveTab} />;
  }

  if (activeTab === 'history') {
    return <History user={user} onLogout={handleLogout} onTabChange={setActiveTab} />;
  }

  return <Upload user={user} onLogout={handleLogout} onTabChange={setActiveTab} />;
}

export default App;
