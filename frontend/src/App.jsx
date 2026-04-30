/**
 * Project: Documents Team
 * Author: Dhinakaran Sekar
 * Email: dhinakaran.s@jubilantenterprises.in
 * Date: 2026-04-30 18:41
 * Description: Main Application component that handles user session management and auto-logout logic.
 */

import React, { useState, useEffect } from 'react';
import Upload from './components/Upload';
import Login from './components/Login';

/**
 * Main App component.
 * Manages the authenticated user state and implements an inactivity timeout.
 */
function App() {
  const [user, setUser] = useState(() => {
    const savedUser = localStorage.getItem('user');
    return savedUser ? JSON.parse(savedUser) : null;
  });

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

  return <Upload user={user} onLogout={handleLogout} />;
}

export default App;
