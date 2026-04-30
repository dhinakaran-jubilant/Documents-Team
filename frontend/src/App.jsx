import React, { useState, useEffect } from 'react';
import Upload from './components/Upload';
import Login from './components/Login';

function App() {
  const [user, setUser] = useState(() => {
    const savedUser = localStorage.getItem('user');
    return savedUser ? JSON.parse(savedUser) : null;
  });

  useEffect(() => {
    if (user) {
      localStorage.setItem('user', JSON.stringify(user));
    } else {
      localStorage.removeItem('user');
    }
  }, [user]);

  const handleLogout = () => {
    setUser(null);
  };

  // Auto-logout after 1 hour of inactivity
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
