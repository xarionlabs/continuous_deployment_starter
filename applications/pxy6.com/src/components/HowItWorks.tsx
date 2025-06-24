
import React from "react";
import { ArrowRight } from "lucide-react";

const HowItWorks = () => {
  return (
    <section id="how-it-works" className="w-full py-12 md:py-24 lg:py-32 bg-gray-50 dark:bg-gray-900">
      <div className="container px-4 md:px-6">
        <div className="flex flex-col items-center justify-center space-y-4 text-center">
          <div className="space-y-2">
            <div className="inline-block rounded-lg bg-primary/10 px-3 py-1 text-sm">
              Process
            </div>
            <h2 className="text-3xl font-bold tracking-tighter md:text-4xl/tight">
              How pxy6 Works
            </h2>
            <p className="mx-auto max-w-[900px] text-gray-600 md:text-xl/relaxed lg:text-base/relaxed xl:text-xl/relaxed dark:text-gray-400">
              Our AI creates and prioritizes hypotheses directly from your data to drive increased sales and conversions.
            </p>
          </div>
        </div>
        
        <div className="mx-auto mt-16 max-w-5xl">
          <div className="grid gap-8 md:grid-cols-3">
            <div className="relative flex flex-col items-center space-y-4 border-t-2 border-primary/30 pt-8 md:items-start md:border-l-2 md:border-t-0 md:pl-8 md:pt-0">
              <div className="absolute -left-3 -top-3 rounded-full bg-primary p-2 text-white md:-left-3 md:-top-0 dark:text-primary-foreground dark:shadow-[0_0_8px_rgba(255,255,255,0.25)]">
                <span className="text-sm font-bold">1</span>
              </div>
              <h3 className="text-xl font-bold">AI-Generated Hypotheses</h3>
              <p className="text-gray-600 dark:text-gray-400 text-sm md:text-base">
                Our AI analyzes your data to create and prioritize strategic recommendation hypotheses based on your specific business goals and customer behavior.
              </p>
            </div>
            <div className="relative flex flex-col items-center space-y-4 border-t-2 border-primary/30 pt-8 md:items-start md:border-l-2 md:border-t-0 md:pl-8 md:pt-0">
              <div className="absolute -left-3 -top-3 rounded-full bg-primary p-2 text-white md:-left-3 md:-top-0 dark:text-primary-foreground dark:shadow-[0_0_8px_rgba(255,255,255,0.25)]">
                <span className="text-sm font-bold">2</span>
              </div>
              <h3 className="text-xl font-bold">Comprehensive A/B Testing</h3>
              <p className="text-gray-600 dark:text-gray-400 text-sm md:text-base">
                We implement improvements on search, related products, and merchandising, then run rigorous A/B tests to validate each hypothesis with real customers.
              </p>
            </div>
            <div className="relative flex flex-col items-center space-y-4 border-t-2 border-primary/30 pt-8 md:items-start md:border-l-2 md:border-t-0 md:pl-8 md:pt-0">
              <div className="absolute -left-3 -top-3 rounded-full bg-primary p-2 text-white md:-left-3 md:-top-0 dark:text-primary-foreground dark:shadow-[0_0_8px_rgba(255,255,255,0.25)]">
                <span className="text-sm font-bold">3</span>
              </div>
              <h3 className="text-xl font-bold">Revenue-Focused Results</h3>
              <p className="text-gray-600 dark:text-gray-400 text-sm md:text-base">
                We track metrics like expected revenue uplift and gradually roll out winning methods to maximize your store's performance and ROI.
              </p>
            </div>
          </div>
          
          <div className="mt-16 flex flex-col items-center space-y-4">
            <div className="flex flex-col items-center space-y-2 text-center">
              <div className="rounded-full border bg-primary p-2 text-white dark:text-primary-foreground dark:shadow-[0_0_8px_rgba(255,255,255,0.25)]">
                <ArrowRight className="h-4 w-4" />
              </div>
              <h3 className="text-xl font-bold">Continuous Optimization</h3>
              <p className="max-w-[600px] text-gray-600 dark:text-gray-400">
                As more data comes in, our system continuously refines and creates new hypotheses, keeping your store at the cutting edge of conversion rate optimization.
              </p>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};

export default HowItWorks;
