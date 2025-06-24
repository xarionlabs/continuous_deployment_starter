
import React from "react";
import { Button } from "@/components/ui/button";
import { DialogTitle, DialogDescription } from "@/components/ui/dialog";
import { PartyPopper } from "lucide-react";

interface ThankYouViewProps {
  onClose: () => void;
  onFastTrack: () => void;
}

const ThankYouView: React.FC<ThankYouViewProps> = ({ onClose, onFastTrack }) => {
  return (
    <div className="flex flex-col items-center space-y-6 py-8 text-center">
      <DialogTitle className="text-xl">Thank you for your information!</DialogTitle>
      <DialogDescription className="text-base">
        We'll use this to provide you with the most relevant solution for your business.
      </DialogDescription>
      
      <div className="flex flex-col space-y-4 w-full max-w-xs">
        <Button 
          variant="outline" 
          onClick={onClose}
          className="w-full"
        >
          Close
        </Button>
        
        {/* Easter egg button */}
        <Button
          variant="ghost"
          onClick={onFastTrack}
          className="text-sm text-muted-foreground hover:text-primary flex items-center gap-2 group transition-all"
        >
          <span>Fast-track Access</span>
          <PartyPopper className="h-4 w-4 group-hover:animate-bounce" />
        </Button>
      </div>
    </div>
  );
};

export default ThankYouView;
