import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { GoogleOAuthProvider } from '@react-oauth/google'
import './index.css'
import App from './App.jsx'

const clientId = import.meta.env.VITE_GOOGLE_CLIENT_ID || "1094200614711-klu4r7t6l5qbv59rscafifn95ejn50pc.apps.googleusercontent.com";

const Root = () => {
  if (!clientId || clientId === "YOUR_GOOGLE_CLIENT_ID") {
    return <App />;
  }
  return (
    <GoogleOAuthProvider clientId={clientId}>
      <App />
    </GoogleOAuthProvider>
  );
};

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <Root />
  </StrictMode>,
);
