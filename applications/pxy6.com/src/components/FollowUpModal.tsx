import React, { useState } from "react";
import { toast } from "sonner";
import { 
  Dialog, 
  DialogContent, 
  DialogDescription, 
  DialogHeader, 
  DialogTitle 
} from "@/components/ui/dialog";
import { FormValues } from "./follow-up/schema";
import FollowUpForm from "./follow-up/FollowUpForm";
import ThankYouView from "./follow-up/ThankYouView";
import BubbleCelebration from "./BubbleCelebration";
import { submitFollowUpInfo, trackLOIClick } from "@/services/followUpService";
import { trackFollowUpComplete, trackLOISubmission } from "@/services/trackingService";

interface FollowUpModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  email: string;
}

const FollowUpModal = ({ open, onOpenChange, email }: FollowUpModalProps) => {
  const [showThankYou, setShowThankYou] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [showCelebration, setShowCelebration] = useState(false);

  const handleSubmit = async (data: FormValues) => {
    if (!email) {
      toast.error("Missing email address. Please try again.");
      return;
    }
    
    try {
      setIsSubmitting(true);
      
      console.log("Starting follow-up form submission for email:", email);
      console.log("Form data:", data);
      
      // Submit the information
      const { error } = await submitFollowUpInfo(email, data);
      
      if (error) {
        console.error("Error saving follow-up information:", error);
        toast.error("Something went wrong. Please try again.");
        return;
      }
      
      // Track LinkedIn conversion
      trackFollowUpComplete();
      
      console.log("Follow-up submission successful");
      toast.success("Thank you for the additional information!");
      setShowThankYou(true);
    } catch (error) {
      console.error("Exception during submission:", error);
      toast.error("Something went wrong. Please try again.");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleEasterEgg = async () => {
    if (!email) {
      console.error("Missing email for LOI tracking");
      toast.error("Could not track your interest. Please try again later.");
      return;
    }
    
    console.log("Easter egg activated for email:", email);
    
    // Track LOI button click in database
    try {
      const { error } = await trackLOIClick(email);
      
      if (error) {
        console.error("Error tracking LOI click:", error);
        // Still continue with celebration and redirect
      } else {
        console.log("LOI click successfully tracked");
      }
    } catch (error) {
      console.error("Exception tracking LOI click:", error);
      // Still continue with celebration and redirect
    }

    // Track LinkedIn conversion before showing celebration
    trackLOISubmission();
    
    // Show bubbles celebration effect
    setShowCelebration(true);
  };
  
  const handleCelebrationComplete = () => {
    // After celebration completes, redirect to external URL
    window.open("https://docuseal.com/d/eeJFwjYc6GtHHk", "_blank");
    toast.success("You found the fast-track! Complete the letter of intent to jump ahead in line.");
    setShowCelebration(false);
  };

  return (
    <>
      <Dialog open={open} onOpenChange={onOpenChange}>
        <DialogContent className="sm:max-w-[550px]">
          {!showThankYou ? (
            <>
              <DialogHeader>
                <DialogTitle>Tell us more about your business</DialogTitle>
                <DialogDescription>
                  Help us understand your needs better so we can provide the most relevant solution.
                </DialogDescription>
              </DialogHeader>
              <FollowUpForm 
                onSubmit={handleSubmit} 
                isSubmitting={isSubmitting} 
              />
            </>
          ) : (
            <ThankYouView 
              onClose={() => onOpenChange(false)} 
              onFastTrack={handleEasterEgg} 
            />
          )}
        </DialogContent>
      </Dialog>
      
      {/* Celebration effect */}
      <BubbleCelebration 
        active={showCelebration} 
        onComplete={handleCelebrationComplete}
      />
    </>
  );
};

export default FollowUpModal;
