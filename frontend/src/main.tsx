import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { QueryClientProvider } from '@tanstack/react-query';
import { AppRouter } from './app/router';
import { queryClient } from './app/queryClient';
import { AppStateProvider } from './stores/AppContext';
import './styles/tokens.css';

if ('serviceWorker' in navigator && import.meta.env.PROD) {
  window.addEventListener('load', () => {
    void navigator.serviceWorker.register('/sw.js');
  });
}

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <AppStateProvider>
        <AppRouter />
      </AppStateProvider>
    </QueryClientProvider>
  </StrictMode>
);
