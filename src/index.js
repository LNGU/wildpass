import React from 'react';
import ReactDOM from 'react-dom';
import './index.css';
import App from './App';
import * as serviceWorkerRegistration from './serviceWorkerRegistration';

ReactDOM.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
  document.getElementById('root')
);

// Register service worker for PWA functionality
serviceWorkerRegistration.register({
  onSuccess: () => {
    console.log('WildPass PWA is ready for offline use!');
  },
  onUpdate: (registration) => {
    console.log('New version available! Refresh to update.');
    // Optionally show a notification to the user
    if (window.confirm('A new version of WildPass is available. Reload to update?')) {
      if (registration && registration.waiting) {
        registration.waiting.postMessage({ type: 'SKIP_WAITING' });
      }
      window.location.reload();
    }
  }
});
