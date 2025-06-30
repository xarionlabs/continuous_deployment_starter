import React, { useState } from "react";
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormMessage,
} from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { insertWaitingList } from "@/services/databaseService";
import { getSourceSummary, trackWaitlistSignup } from "@/services/trackingService";
import FollowUpModal from "./FollowUpModal";

// Schema for email validation
const formSchema = z.object({
  email: z.string().email("Please enter a valid email address"),
});

type FormValues = z.infer<typeof formSchema>;

const WaitlistForm = () => {
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
      // Get the UTM parameters
      const utmParams = getSourceSummary();
      
      // Get hero and ad variants from URL
      const urlParams = new URLSearchParams(window.location.search);
      const heroVariation = urlParams.get('variation') || 'A';
      const adVariant = urlParams.get('utm_content') || 'default';
      
      // Create a structured source object
      const sourceData = {
        button_source: "who_we_serve_section",
        utm_params: utmParams,
        hero_variation: heroVariation,
        ad_variant: adVariant,
        timestamp: new Date().toISOString()
      };
      
      // Insert email into waiting_list table with source
      const { error } = await insertWaitingList(
        data.email,
        JSON.stringify(sourceData)
      );

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
      
      toast.success("You're on the list! 🎉");
    } catch (error) {
      console.error("Exception during submission:", error);
      toast.error("Something went wrong. Please try again.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <>
      <Form {...form}>
        <form onSubmit={form.handleSubmit(onSubmit)} className="flex flex-col sm:flex-row gap-4 max-w-md mx-auto mt-8">
          <FormField
            control={form.control}
            name="email"
            render={({ field }) => (
              <FormItem className="flex-1">
                <FormControl>
                  <Input 
                    placeholder="Enter your email" 
                    type="email" 
                    {...field} 
                    className="h-12"
                  />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
          <Button 
            type="submit" 
            className="h-12 px-8"
            disabled={isSubmitting}
          >
            {isSubmitting ? "Submitting..." : "Join Waitlist"}
          </Button>
        </form>
      </Form>

      {/* Follow-up modal */}
      <FollowUpModal
        open={showFollowUp}
        onOpenChange={setShowFollowUp}
        email={submittedEmail}
      />
    </>
  );
};

export default WaitlistForm; 