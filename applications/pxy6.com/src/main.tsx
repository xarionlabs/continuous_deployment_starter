
import { createRoot } from 'react-dom/client'
import App from './App.tsx'
import './index.css'
import { initializeTracking } from './services/trackingService'

// Initialize tracking when the app loads
initializeTracking();

createRoot(document.getElementById("root")!).render(<App />);
