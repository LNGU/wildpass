import React, { useState, useEffect, useCallback } from 'react';
import { loginWithGoogle, isAuthenticated, getUser, logout } from '../services/auth';

const GOOGLE_CLIENT_ID = process.env.REACT_APP_GOOGLE_CLIENT_ID;

function AuthGate({ children }) {
  const [authed, setAuthed] = useState(isAuthenticated());
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleCredentialResponse = useCallback(async (response) => {
    setLoading(true);
    setError(null);
    try {
      await loginWithGoogle(response.credential);
      setAuthed(true);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (authed || !GOOGLE_CLIENT_ID) return;

    const initGoogle = () => {
      if (!window.google?.accounts?.id) {
        setTimeout(initGoogle, 200);
        return;
      }
      window.google.accounts.id.initialize({
        client_id: GOOGLE_CLIENT_ID,
        callback: handleCredentialResponse,
      });
      window.google.accounts.id.renderButton(
        document.getElementById('google-signin-btn'),
        { theme: 'filled_blue', size: 'large', width: 300, text: 'signin_with' }
      );
    };
    initGoogle();
  }, [authed, handleCredentialResponse]);

  const handleLogout = useCallback(() => {
    logout();
    setAuthed(false);
  }, []);

  if (!GOOGLE_CLIENT_ID) {
    // No client ID configured — skip auth entirely
    return <>{children}</>;
  }

  if (authed) {
    const user = getUser();
    return (
      <>
        <div style={{
          position: 'fixed', top: 12, right: 16, zIndex: 9999,
          display: 'flex', alignItems: 'center', gap: 8,
        }}>
          {user?.picture && (
            <img src={user.picture} alt="" style={{
              width: 32, height: 32, borderRadius: '50%', border: '2px solid rgba(255,255,255,0.3)',
            }} />
          )}
          <span style={{ color: 'rgba(255,255,255,0.8)', fontSize: 13 }}>
            {user?.name || user?.email || ''}
          </span>
          <button onClick={handleLogout} style={{
            background: 'rgba(255,255,255,0.15)', border: '1px solid rgba(255,255,255,0.2)',
            color: 'rgba(255,255,255,0.8)', borderRadius: 6, padding: '4px 10px',
            cursor: 'pointer', fontSize: 12,
          }}>
            Sign out
          </button>
        </div>
        {children}
      </>
    );
  }

  return (
    <div style={{
      minHeight: '100vh',
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      background: 'linear-gradient(135deg, #0f0c29 0%, #1a1a4e 50%, #24243e 100%)',
    }}>
      <div style={{
        background: 'rgba(255,255,255,0.07)',
        backdropFilter: 'blur(20px)',
        borderRadius: 20, padding: '48px 40px', textAlign: 'center',
        border: '1px solid rgba(255,255,255,0.1)',
        boxShadow: '0 20px 60px rgba(0,0,0,0.5)',
        maxWidth: 400, width: '90%',
      }}>
        <div style={{ fontSize: 48, marginBottom: 8 }}>✈️</div>
        <h1 style={{
          color: '#fff', fontSize: 32, fontWeight: 700, margin: '0 0 8px',
          letterSpacing: '-0.5px',
        }}>
          WildPass
        </h1>
        <p style={{
          color: 'rgba(255,255,255,0.5)', fontSize: 15, margin: '0 0 32px',
        }}>
          Sign in to search flights
        </p>

        <div id="google-signin-btn" style={{
          display: 'flex', justifyContent: 'center', minHeight: 44,
        }}></div>

        {loading && (
          <p style={{ color: 'rgba(255,255,255,0.6)', marginTop: 16, fontSize: 14 }}>
            Signing in...
          </p>
        )}
        {error && (
          <p style={{ color: '#ff6b6b', marginTop: 16, fontSize: 14 }}>
            {error}
          </p>
        )}
      </div>
    </div>
  );
}

export default AuthGate;
