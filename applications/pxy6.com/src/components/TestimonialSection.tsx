import React from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Rocket, Target, Compass } from "lucide-react";

const TestimonialSection = () => {
  return (
    <section id="testimonials" className="w-full py-12 md:py-24 lg:py-32 bg-gray-50 dark:bg-gray-900">
      <div className="container px-4 md:px-6">
        <div className="flex flex-col items-center justify-center space-y-4 text-center">
          <div className="space-y-2">
            <div className="inline-block rounded-lg bg-primary/10 px-3 py-1 text-sm">
              Vision
            </div>
            <h2 className="text-3xl font-bold tracking-tighter md:text-4xl/tight">
              Seeking Visionary Collaborators
            </h2>
            <p className="mx-auto max-w-[900px] text-gray-600 md:text-xl/relaxed lg:text-base/relaxed xl:text-xl/relaxed dark:text-gray-400">
              We're looking for forward-thinking fashion stores who want to shape the future of ecommerce personalization.
            </p>
          </div>
        </div>
        
        <div className="mx-auto mt-12 grid max-w-5xl gap-6 md:grid-cols-3">
          <Card className="border-none shadow-lg transition-all duration-300 hover:scale-[1.02] dark:bg-gray-800 dark:text-white">
            <CardContent className="p-6">
              <div className="space-y-4">
                <div className="flex items-center space-x-4">
                  <div className="h-10 w-10 rounded-full bg-primary/20 flex items-center justify-center text-primary transition-transform hover:scale-110 dark:bg-primary/20 dark:text-white">
                    <Rocket className="h-5 w-5" />
                  </div>
                  <div>
                    <div className="font-medium">Early Adopter Benefits</div>
                    <div className="text-sm text-gray-500 dark:text-gray-400">Fashion Pioneers</div>
                  </div>
                </div>
                <div className="border-t pt-4">
                  <ul className="space-y-2 text-sm">
                    <li>• Direct input on feature development</li>
                    <li>• Early access to cutting-edge tech</li>
                    <li>• Personalized onboarding support</li>
                  </ul>
                </div>
                <p className="text-gray-600 dark:text-gray-400 text-sm italic">
                  "Join us in creating the next generation of personalized shopping experiences for fashion."
                </p>
              </div>
            </CardContent>
          </Card>
          
          <Card className="border-none shadow-lg transition-all duration-300 hover:scale-[1.02] dark:bg-gray-800 dark:text-white">
            <CardContent className="p-6">
              <div className="space-y-4">
                <div className="flex items-center space-x-4">
                  <div className="h-10 w-10 rounded-full bg-primary/20 flex items-center justify-center text-primary transition-transform hover:scale-110 dark:bg-primary/20 dark:text-white">
                    <Target className="h-5 w-5" />
                  </div>
                  <div>
                    <div className="font-medium">Ideal Collaboration Profile</div>
                    <div className="text-sm text-gray-500 dark:text-gray-400">Growth-Focused Stores</div>
                  </div>
                </div>
                <div className="border-t pt-4">
                  <ul className="space-y-2 text-sm">
                    <li>• 250k+ monthly site visitors</li>
                    <li>• Shopify-based fashion</li>
                    <li>• Forward-thinking leadership</li>
                  </ul>
                </div>
                <p className="text-gray-600 dark:text-gray-400 text-sm italic">
                  "We're seeking partners who are ready to push the boundaries of what's possible in fashion ecommerce."
                </p>
              </div>
            </CardContent>
          </Card>
          
          <Card className="border-none shadow-lg transition-all duration-300 hover:scale-[1.02] dark:bg-gray-800 dark:text-white">
            <CardContent className="p-6">
              <div className="space-y-4">
                <div className="flex items-center space-x-4">
                  <div className="h-10 w-10 rounded-full bg-primary/20 flex items-center justify-center text-primary transition-transform hover:scale-110 dark:bg-primary/20 dark:text-white">
                    <Compass className="h-5 w-5" />
                  </div>
                  <div>
                    <div className="font-medium">Vision for the Future</div>
                    <div className="text-sm text-gray-500 dark:text-gray-400">Building Together</div>
                  </div>
                </div>
                <div className="border-t pt-4">
                  <ul className="space-y-2 text-sm">
                    <li>• AI-driven personalization</li>
                    <li>• Data-backed recommendations</li>
                    <li>• Continuous experimentation</li>
                  </ul>
                </div>
                <p className="text-gray-600 dark:text-gray-400 text-sm italic">
                  "Help us redefine how shoppers discover and fall in love with products that truly match their preferences."
                </p>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </section>
  );
};

export default TestimonialSection;
