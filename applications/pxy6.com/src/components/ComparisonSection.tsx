
import React from "react";
import { CheckCircle, XCircle } from "lucide-react";

const ComparisonSection = () => {
  return (
    <section id="comparison" className="w-full py-12 md:py-24 lg:py-32">
      <div className="container px-4 md:px-6">
        <div className="flex flex-col items-center justify-center space-y-4 text-center">
          <div className="space-y-2">
            <div className="inline-block rounded-lg bg-primary/10 px-3 py-1 text-sm">
              Comparison
            </div>
            <h2 className="text-3xl font-bold tracking-tighter md:text-4xl/tight">
              Why Choose Hypothesis-Driven Recommendations?
            </h2>
            <p className="mx-auto max-w-[900px] text-gray-600 md:text-xl/relaxed lg:text-base/relaxed xl:text-xl/relaxed dark:text-gray-400">
              See how our approach goes beyond traditional recommendation systems to deliver better business results.
            </p>
          </div>
        </div>
        
        <div className="mx-auto mt-16 max-w-5xl">
          <div className="grid gap-8 md:grid-cols-2">
            <div className="rounded-xl border border-gray-200 bg-white p-6 dark:border-gray-800 dark:bg-gray-950">
              <h3 className="mb-4 text-xl font-bold text-gray-900 dark:text-gray-50">Traditional Recommendation Systems</h3>
              <ul className="space-y-4">
                <li className="flex items-start">
                  <XCircle className="mr-2 h-5 w-5 shrink-0 text-red-500" />
                  <span>Focus only on "frequently bought together" patterns</span>
                </li>
                <li className="flex items-start">
                  <XCircle className="mr-2 h-5 w-5 shrink-0 text-red-500" />
                  <span>Not aligned with strategic business goals</span>
                </li>
                <li className="flex items-start">
                  <XCircle className="mr-2 h-5 w-5 shrink-0 text-red-500" />
                  <span>Limited testing capabilities</span>
                </li>
                <li className="flex items-start">
                  <XCircle className="mr-2 h-5 w-5 shrink-0 text-red-500" />
                  <span>One-size-fits-all approach</span>
                </li>
                <li className="flex items-start">
                  <XCircle className="mr-2 h-5 w-5 shrink-0 text-red-500" />
                  <span>No continuous optimization framework</span>
                </li>
                <li className="flex items-start">
                  <CheckCircle className="mr-2 h-5 w-5 shrink-0 text-green-500" />
                  <span>Basic product affinity detection</span>
                </li>
              </ul>
            </div>
            <div className="rounded-xl border border-primary bg-primary/5 p-6 shadow-lg">
              <h3 className="mb-4 text-xl font-bold text-primary">pxy6 Hypothesis-Driven Approach</h3>
              <ul className="space-y-4">
                <li className="flex items-start">
                  <CheckCircle className="mr-2 h-5 w-5 shrink-0 text-green-500" />
                  <span>Strategic recommendations aligned with business goals</span>
                </li>
                <li className="flex items-start">
                  <CheckCircle className="mr-2 h-5 w-5 shrink-0 text-green-500" />
                  <span>Optimized for upselling, cross-selling, and conversion</span>
                </li>
                <li className="flex items-start">
                  <CheckCircle className="mr-2 h-5 w-5 shrink-0 text-green-500" />
                  <span>Systematic A/B testing of recommendation strategies</span>
                </li>
                <li className="flex items-start">
                  <CheckCircle className="mr-2 h-5 w-5 shrink-0 text-green-500" />
                  <span>Tailored to your specific product catalog and customers</span>
                </li>
                <li className="flex items-start">
                  <CheckCircle className="mr-2 h-5 w-5 shrink-0 text-green-500" />
                  <span>Continuous improvement framework</span>
                </li>
                <li className="flex items-start">
                  <CheckCircle className="mr-2 h-5 w-5 shrink-0 text-green-500" />
                  <span>Advanced product relationship insights</span>
                </li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};

export default ComparisonSection;
