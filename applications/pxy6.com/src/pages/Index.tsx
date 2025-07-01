import React, { useState } from "react";
import { Button } from "@/components/ui/button";
import HeroABTest from "@/components/HeroABTest";
import Features from "@/components/Features";
import HowItWorks from "@/components/HowItWorks";
import ComparisonSection from "@/components/ComparisonSection";
import TestimonialSection from "@/components/TestimonialSection";
import Footer from "@/components/Footer";
import Navbar from "@/components/Navbar";
import WaitingListModal from "@/components/WaitingListModal";
import WaitlistForm from "@/components/WaitlistForm";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { MetricsDashboard } from "@/components/MetricsDashboard";

const Index = () => {
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [modalContext, setModalContext] = useState<"login" | "try">("try");

  const handleOpenModal = () => {
    setModalContext("try");
    setIsModalOpen(true);
  };

  return (
    <div className="min-h-screen bg-gradient-to-b from-gray-50 to-gray-100 dark:from-gray-900 dark:to-gray-800">
      <Navbar />
      <HeroABTest />
      
      {/* Target Audience Section - Moved up to immediately establish relevance */}
      <section className="py-16 bg-white dark:bg-gray-800/50">
        <div className="container px-4 md:px-6">
          <div className="text-center mb-12">
            <h2 className="text-3xl font-bold tracking-tighter mb-4 sm:text-4xl md:text-5xl">
              Who We Serve
            </h2>
            <p className="mx-auto max-w-[800px] text-gray-600 dark:text-gray-400 md:text-xl">
              Our AI-powered product recommendations are specifically designed for fashion stores 
              with significant monthly traffic.
            </p>
            <p className="mx-auto max-w-[800px] text-primary font-medium mt-2 md:text-lg">
              Ideal for Shopify stores with 250,000+ monthly visitors
            </p>
          </div>
          <WaitlistForm />
        </div>
      </section>

      {/* Metrics Dashboard Section - Moved up to show immediate value */}
      <section className="py-16 bg-white dark:bg-gray-800">
        <div className="container px-4 md:px-6">
          <MetricsDashboard />
        </div>
      </section>

      <Features />
      <TestimonialSection />
      <HowItWorks />
      <ComparisonSection />
      
      {/* Pricing Section */}
      <section className="py-16 bg-gray-50 dark:bg-gray-900/50">
        <div className="container px-4 md:px-6">
          <div className="text-center mb-12">
            <h2 className="text-3xl font-bold tracking-tighter mb-4 sm:text-4xl md:text-5xl">
              Transparent Pricing
            </h2>
            <p className="mx-auto max-w-[700px] text-gray-600 dark:text-gray-400 md:text-xl">
              Our pricing scales with your traffic to ensure you get the best ROI as your store grows.
            </p>
          </div>
          
          <div className="grid gap-6 md:grid-cols-3 md:gap-8 max-w-5xl mx-auto">
            {/* Build Plan */}
            <Card className="flex flex-col h-full shadow-lg">
              <CardHeader>
                <CardTitle className="text-2xl">Build</CardTitle>
              </CardHeader>
              <CardContent className="flex-1 space-y-4">
                <div>
                  <div className="text-4xl font-bold">250-500k</div>
                  <p className="text-gray-500 dark:text-gray-400">Monthly visitors</p>
                </div>
                <div className="border-t border-gray-200 dark:border-gray-700 pt-4">
                  <ul className="space-y-2">
                    <li>Free to install</li>
                    <li className="font-semibold">€800 per month</li>
                    <li>Traffic-based multiplier</li>
                  </ul>
                </div>
              </CardContent>
            </Card>
            
            {/* Scale Plan */}
            <Card className="flex flex-col h-full shadow-lg border-primary">
              <CardHeader>
                <CardTitle className="text-2xl">Scale</CardTitle>
              </CardHeader>
              <CardContent className="flex-1 space-y-4">
                <div>
                  <div className="text-4xl font-bold">500k-1M</div>
                  <p className="text-gray-500 dark:text-gray-400">Monthly visitors</p>
                </div>
                <div className="border-t border-gray-200 dark:border-gray-700 pt-4">
                  <ul className="space-y-2">
                    <li>Free to install</li>
                    <li className="font-semibold">€1,600 per month</li>
                    <li>Traffic-based multiplier</li>
                  </ul>
                </div>
              </CardContent>
            </Card>
            
            {/* Elevate Plan */}
            <Card className="flex flex-col h-full shadow-lg">
              <CardHeader>
                <CardTitle className="text-2xl">Elevate</CardTitle>
              </CardHeader>
              <CardContent className="flex-1 space-y-4">
                <div>
                  <div className="text-4xl font-bold">1M+</div>
                  <p className="text-gray-500 dark:text-gray-400">Monthly visitors</p>
                </div>
                <div className="border-t border-gray-200 dark:border-gray-700 pt-4">
                  <ul className="space-y-2">
                    <li>Free to install</li>
                    <li className="font-semibold">€3,200 per month</li>
                    <li>Traffic-based multiplier</li>
                  </ul>
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      </section>
      
      {/* CTA Section */}
      <section className="py-16 bg-primary/5">
        <div className="container px-4 md:px-6">
          <div className="flex flex-col items-center justify-center space-y-4 text-center">
            <div className="space-y-2">
              <h2 className="text-3xl font-bold tracking-tighter sm:text-4xl md:text-5xl">
                Ready to Shape the Future of CRO?
              </h2>
              <p className="mx-auto max-w-[700px] text-gray-600 md:text-xl dark:text-gray-400">
                We're looking for CRO-obsessed early adopters — especially Shopify fashion stores with 250k+ monthly visitors — to shape 
                the future of conversion rate optimization with us.
              </p>
            </div>
            <div className="flex flex-col sm:flex-row gap-4">
              <Button 
                size="lg" 
                className="bg-primary hover:bg-primary/90"
                onClick={handleOpenModal}
              >
                Join Waitlist
              </Button>
            </div>
          </div>
        </div>
      </section>
      
      <Footer />
      
      {/* Waiting List Modal */}
      <WaitingListModal 
        open={isModalOpen} 
        onOpenChange={setIsModalOpen} 
        context={modalContext}
      />
    </div>
  );
};

export default Index;
