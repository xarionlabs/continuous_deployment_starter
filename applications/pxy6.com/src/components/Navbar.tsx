import React from "react";
import { Button } from "@/components/ui/button";
import { ThemeToggle } from "@/components/ThemeToggle";
import WaitingListModal from "@/components/WaitingListModal";
import { useState } from "react";

const Navbar = () => {
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [modalContext, setModalContext] = useState<"login" | "try">("try");

  const handleTryFreeClick = () => {
    setModalContext("try");
    setIsModalOpen(true);
  };

  return (
    <header className="sticky top-0 z-50 w-full border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="container flex h-16 items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-2xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-primary to-purple-600">
            pxy6
          </span>
        </div>
        <nav className="hidden md:flex items-center gap-6">
          <a href="#features" className="text-sm font-medium hover:text-primary">
            Features
          </a>
          <a href="#how-it-works" className="text-sm font-medium hover:text-primary">
            Process
          </a>
          <a href="#comparison" className="text-sm font-medium hover:text-primary">
            Comparison
          </a>
          <a href="#testimonials" className="text-sm font-medium hover:text-primary">
            Vision
          </a>
        </nav>
        <div className="flex items-center gap-4">
          <ThemeToggle />
          <Button size="sm" onClick={handleTryFreeClick}>
            Join Waitlist
          </Button>
        </div>
      </div>
      
      {/* Customized Waiting List Modal */}
      <WaitingListModal 
        open={isModalOpen} 
        onOpenChange={setIsModalOpen} 
        context={modalContext}
      />
    </header>
  );
};

export default Navbar;
