import { Toaster } from "@/components/ui/toaster";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Routes, Route, useLocation } from "react-router-dom";
import { ThemeProvider } from "@/providers/ThemeProvider";
import Index from "./pages/Index";
import NotFound from "./pages/NotFound";
import ClarityAnalytics from "@/components/ClarityAnalytics";
import { useEffect } from "react";
import { initializeGA } from "@/services/analyticsService";
import { useAnalytics } from "@/hooks/useAnalytics";

const queryClient = new QueryClient();

// Analytics wrapper component
const AnalyticsWrapper = ({ children }: { children: React.ReactNode }) => {
  const location = useLocation();
  
  // Initialize GA on mount
  useEffect(() => {
    initializeGA();
  }, []);

  // Track page views and scroll depth
  useAnalytics(location.pathname);

  return <>{children}</>;
};

const App = () => (
  <ThemeProvider defaultTheme="system" storageKey="pxy6-theme">
    <QueryClientProvider client={queryClient}>
      <TooltipProvider>
        <Toaster />
        <Sonner />
        <ClarityAnalytics />
        <BrowserRouter>
          <AnalyticsWrapper>
            <Routes>
              <Route path="/" element={<Index />} />
              {/* ADD ALL CUSTOM ROUTES ABOVE THE CATCH-ALL "*" ROUTE */}
              <Route path="*" element={<NotFound />} />
            </Routes>
          </AnalyticsWrapper>
        </BrowserRouter>
      </TooltipProvider>
    </QueryClientProvider>
  </ThemeProvider>
);

export default App;
