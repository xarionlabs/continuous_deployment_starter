import React, { useState } from "react";
import { Button } from "@/components/ui/button";
import { ArrowRight, Compass, TrendingUp, Zap } from "lucide-react";
import WaitingListModal from "./WaitingListModal";

const Hero = () => {
  const [isModalOpen, setIsModalOpen] = useState(false);

  return (
    <section className="w-full flex items-center justify-center min-h-[calc(100vh-80px)]">
      <div className="container px-4 md:px-6 py-16 md:py-20">
        <div className="grid gap-6 lg:grid-cols-[1fr_400px] lg:gap-12 xl:grid-cols-[1fr_600px]">
          <div className="flex flex-col justify-center space-y-6">
            <div className="inline-flex items-center rounded-full border px-3 py-1 text-sm transition-colors hover:bg-accent hover:text-accent-foreground">
              <Zap className="mr-2 h-4 w-4 text-primary" />
              <span>Boost Your Store's Revenue</span>
            </div>
            <h1 className="text-4xl font-bold tracking-tighter sm:text-5xl xl:text-6xl/none">
              Transform Your <br />
              <span className="bg-clip-text text-transparent bg-gradient-to-r from-primary to-purple-600">
                Product Recommendations
              </span>
            </h1>
            <div className="space-y-4">
              <div className="flex items-center gap-2 text-lg text-gray-600 dark:text-gray-400">
                <TrendingUp className="h-5 w-5 text-primary" />
                <span>Increase average basket size by up to 9.5%</span>
              </div>
              <div className="flex items-center gap-2 text-lg text-gray-600 dark:text-gray-400">
                <TrendingUp className="h-5 w-5 text-primary" />
                <span>Boost conversion rates by 15.2%</span>
              </div>
              <div className="flex items-center gap-2 text-lg text-gray-600 dark:text-gray-400">
                <TrendingUp className="h-5 w-5 text-primary" />
                <span>Improve upsell success by 23.8%</span>
              </div>
            </div>
            <p className="max-w-[600px] text-gray-600 md:text-xl dark:text-gray-400">
              AI-powered product recommendations that go beyond "frequently bought together" to drive real business results.
            </p>
            <div className="flex flex-col gap-2 min-[400px]:flex-row">
              <Button 
                className="inline-flex h-12 items-center justify-center rounded-md bg-primary px-8 text-base font-medium text-primary-foreground shadow transition-colors hover:bg-primary/90 focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:pointer-events-none disabled:opacity-50"
                onClick={() => setIsModalOpen(true)}
              >
                Join Waitlist
                <ArrowRight className="ml-2 h-5 w-5" />
              </Button>
            </div>
          </div>
          <div className="flex items-center justify-center">
            <div className="relative w-full aspect-square md:aspect-[4/3] lg:aspect-square overflow-hidden rounded-xl bg-muted/80 shadow-lg">
              <div className="absolute inset-0 bg-gradient-to-tr from-purple-500/20 to-primary/10 rounded-xl">
                <div className="h-full w-full p-4 md:p-8 flex items-center justify-center">
                  <div className="bg-black/80 backdrop-blur-sm p-4 md:p-8 rounded-lg w-full max-w-md text-white">
                    <h3 className="text-lg font-bold mb-4 flex items-center gap-2">
                      <span className="bg-emerald-500 dark:bg-emerald-400 rounded-full p-1 inline-flex">
                        <Compass className="h-4 w-4 text-white" />
                      </span>
                      Real Results from Early Adopters
                    </h3>
                    <div className="space-y-3">
                      <div className="flex justify-between items-center">
                        <span>Average Basket Size:</span>
                        <span className="font-bold text-emerald-500">+9.5%</span>
                      </div>
                      <div className="flex justify-between items-center">
                        <span>Conversion Rate:</span>
                        <span className="font-bold text-emerald-500">+15.2%</span>
                      </div>
                      <div className="flex justify-between items-center">
                        <span>Upsell Success:</span>
                        <span className="font-bold text-emerald-500">+23.8%</span>
                      </div>
                      <div className="mt-6 text-sm text-gray-300">
                        * Based on preliminary research and target outcomes
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
      
      {/* Waiting List Modal */}
      <WaitingListModal open={isModalOpen} onOpenChange={setIsModalOpen} />
    </section>
  );
};

export default Hero;
