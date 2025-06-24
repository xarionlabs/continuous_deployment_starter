import React, { useState } from "react";
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { toast } from "sonner";
import { 
  Dialog, 
  DialogContent, 
  DialogDescription, 
  DialogHeader, 
  DialogTitle 
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormMessage,
} from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { supabase } from "@/integrations/supabase/client";
import { getSourceSummary, trackWaitlistSignup } from "@/services/trackingService";
import FollowUpModal from "./FollowUpModal";

// Schema for email validation
const formSchema = z.object({
  email: z.string().email("Please enter a valid email address"),
});

type FormValues = z.infer<typeof formSchema>;

interface WaitingListModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  context?: "login" | "try";
}

const WaitingListModal = ({ open, onOpenChange, context = "login" }: WaitingListModalProps) => {
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [showFollowUp, setShowFollowUp] = useState(false);
  const [submittedEmail, setSubmittedEmail] = useState("");

  const form = useForm<FormValues>({
    resolver: zodResolver(formSchema),
    defaultValues: {
      email: "",
    },
  });

  const onSubmit = async (data: FormValues) => {
    setIsSubmitting(true);
    try {
      // Get the button context source
      const buttonSource = context === "login" ? "navbar_login" : "cta_try_free";
      
      // Get the UTM parameters
      const utmParams = getSourceSummary();
      
      // Get hero and ad variants from URL
      const urlParams = new URLSearchParams(window.location.search);
      const heroVariation = urlParams.get('variation') || 'A';
      const adVariant = urlParams.get('utm_content') || 'default';
      
      // Create a structured source object
      const sourceData = {
        button_source: buttonSource,
        utm_params: utmParams,
        hero_variation: heroVariation,
        ad_variant: adVariant,
        timestamp: new Date().toISOString()
      };
      
      // Log the submission data for debugging
      console.log("Submitting to waiting_list:", {
        email: data.email,
        source: JSON.stringify(sourceData)
      });
      
      // Insert email into Supabase waiting_list table with source
      const { error } = await supabase
        .from('waiting_list')
        .insert([{ 
          email: data.email,
          source: JSON.stringify(sourceData)
        }]);

      if (error) {
        console.error("Error submitting to waiting list:", error);
        toast.error("Something went wrong. Please try again.");
        return;
      }

      // Track LinkedIn conversion
      trackWaitlistSignup();
      
      // Show follow-up modal
      setSubmittedEmail(data.email);
      setShowFollowUp(true);
      onOpenChange(false);
      
      toast.success("You're on the list! 🎉");
    } catch (error) {
      console.error("Exception during submission:", error);
      toast.error("Something went wrong. Please try again.");
    } finally {
      setIsSubmitting(false);
    }
  };

  // Set title and description based on context
  const getTitle = () => {
    return context === "login" ? "Join our Login Waiting List" : "Get Early Access";
  };

  const getDescription = () => {
    return context === "login" 
      ? "Enter your email to be notified when user accounts are available."
      : "Enter your email to be notified when our free trial is available.";
  };

  const getButtonText = () => {
    return "Join Waitlist";
  };

  return (
    <>
      <Dialog open={open} onOpenChange={onOpenChange}>
        <DialogContent className="sm:max-w-[425px]">
          <DialogHeader>
            <DialogTitle>{getTitle()}</DialogTitle>
            <DialogDescription>
              {getDescription()}
            </DialogDescription>
          </DialogHeader>
          <Form {...form}>
            <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
              <FormField
                control={form.control}
                name="email"
                render={({ field }) => (
                  <FormItem>
                    <FormControl>
                      <Input 
                        placeholder="Your email address" 
                        type="email" 
                        {...field} 
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <Button 
                type="submit" 
                className="w-full" 
                disabled={isSubmitting}
              >
                {isSubmitting ? "Submitting..." : getButtonText()}
              </Button>
            </form>
          </Form>
        </DialogContent>
      </Dialog>

      {/* Follow-up modal */}
      <FollowUpModal
        open={showFollowUp}
        onOpenChange={setShowFollowUp}
        email={submittedEmail}
      />
    </>
  );
};

export default WaitingListModal;
