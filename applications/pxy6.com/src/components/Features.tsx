import React, { useEffect } from "react";
import { 
  LineChart, 
  BarChart, 
  ShoppingBag, 
  TrendingUp, 
  Lightbulb, 
  BarChartHorizontal 
} from "lucide-react";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { trackFeatureView } from "@/services/analyticsService";

const Features = () => {
  // Track feature views when component mounts
  useEffect(() => {
    trackFeatureView('hypothesis_driven');
    trackFeatureView('data_driven');
    trackFeatureView('strategic_goals');
  }, []);

  return (
    <section id="features" className="w-full py-12 md:py-24 lg:py-32 bg-white dark:bg-gray-950">
      <div className="container px-4 md:px-6">
        <div className="flex flex-col items-center justify-center space-y-4 text-center">
          <div className="space-y-2">
            <div className="inline-block rounded-lg bg-primary/10 px-3 py-1 text-sm">
              Features
            </div>
            <h2 className="text-3xl font-bold tracking-tighter md:text-4xl/tight">
              Beyond Traditional Recommendation Systems
            </h2>
            <p className="mx-auto max-w-[900px] text-gray-600 md:text-xl/relaxed lg:text-base/relaxed xl:text-xl/relaxed dark:text-gray-400">
              Our platform bridges the gap between data-driven insights and strategic business goals,
              enabling you to create recommendation hypotheses that drive real results.
            </p>
          </div>
        </div>
        <div className="mx-auto grid max-w-5xl grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3 mt-12">
          <Card className="flex flex-col items-center text-center border-none shadow-md transition-all duration-300 hover:scale-[1.02] bg-gradient-to-br from-primary/5 to-primary/10 dark:from-primary/10 dark:to-primary/20 dark:text-white">
            <CardHeader>
              <div className="flex flex-col items-center space-y-2">
                <div className="p-2 bg-emerald-100/50 dark:bg-emerald-800/20 rounded-full inline-flex transition-transform group-hover:scale-110">
                  <TrendingUp className="h-6 w-6 text-emerald-600 dark:text-emerald-400" />
                </div>
                <CardTitle>Strategic Recommendations</CardTitle>
              </div>
              <CardDescription className="dark:text-gray-300">
                Optimize for business goals beyond "frequently bought together"
              </CardDescription>
            </CardHeader>
            <CardContent className="flex-grow">
              <p className="text-sm text-muted-foreground dark:text-gray-400">
                Create recommendation strategies aligned with specific business goals like upselling, cross-selling, and increasing conversion rates.
              </p>
            </CardContent>
          </Card>
          
          <Card className="flex flex-col items-center text-center border-none shadow-md transition-all duration-300 hover:scale-[1.02] bg-gradient-to-br from-emerald-50/50 to-primary/10 dark:from-emerald-900/10 dark:to-primary/20 dark:text-white">
            <CardHeader>
              <div className="flex flex-col items-center space-y-2">
                <div className="p-2 bg-emerald-100/50 dark:bg-emerald-800/20 rounded-full inline-flex transition-transform group-hover:scale-110">
                  <Lightbulb className="h-6 w-6 text-emerald-600 dark:text-emerald-400" />
                </div>
                <CardTitle>Hypothesis Testing</CardTitle>
              </div>
              <CardDescription className="dark:text-gray-300">
                Systematically test recommendation strategies
              </CardDescription>
            </CardHeader>
            <CardContent className="flex-grow">
              <p className="text-sm text-muted-foreground dark:text-gray-400">
                Generate and validate recommendation hypotheses through A/B testing and experimentation to find what works best for your customers.
              </p>
            </CardContent>
          </Card>
          
          <Card className="flex flex-col items-center text-center border-none shadow-md transition-all duration-300 hover:scale-[1.02] bg-gradient-to-br from-primary/5 to-primary/10 dark:from-primary/10 dark:to-primary/20 dark:text-white">
            <CardHeader>
              <div className="flex flex-col items-center space-y-2">
                <div className="p-2 bg-emerald-100/50 dark:bg-emerald-800/20 rounded-full inline-flex transition-transform group-hover:scale-110">
                  <LineChart className="h-6 w-6 text-emerald-600 dark:text-emerald-400" />
                </div>
                <CardTitle>Data-Driven Insights</CardTitle>
              </div>
              <CardDescription className="dark:text-gray-300">
                Analyze results with clear metrics
              </CardDescription>
            </CardHeader>
            <CardContent className="flex-grow">
              <p className="text-sm text-muted-foreground dark:text-gray-400">
                Track performance with meaningful metrics like Average Basket Size (ABS), conversion rates, and other KPIs that matter to your business.
              </p>
            </CardContent>
          </Card>
          
          <Card className="flex flex-col items-center text-center border-none shadow-md transition-all duration-300 hover:scale-[1.02] bg-gradient-to-br from-emerald-50/50 to-primary/10 dark:from-emerald-900/10 dark:to-primary/20 dark:text-white">
            <CardHeader>
              <div className="flex flex-col items-center space-y-2">
                <div className="p-2 bg-emerald-100/50 dark:bg-emerald-800/20 rounded-full inline-flex transition-transform group-hover:scale-110">
                  <ShoppingBag className="h-6 w-6 text-emerald-600 dark:text-emerald-400" />
                </div>
                <CardTitle>Shopify Integration</CardTitle>
              </div>
              <CardDescription className="dark:text-gray-300">
                Seamless integration with your Shopify store
              </CardDescription>
            </CardHeader>
            <CardContent className="flex-grow">
              <p className="text-sm text-muted-foreground dark:text-gray-400">
                Easy setup with your existing Shopify store, with no technical expertise required to start running experiments.
              </p>
            </CardContent>
          </Card>
          
          <Card className="flex flex-col items-center text-center border-none shadow-md transition-all duration-300 hover:scale-[1.02] bg-gradient-to-br from-primary/5 to-primary/10 dark:from-primary/10 dark:to-primary/20 dark:text-white">
            <CardHeader>
              <div className="flex flex-col items-center space-y-2">
                <div className="p-2 bg-emerald-100/50 dark:bg-emerald-800/20 rounded-full inline-flex transition-transform group-hover:scale-110">
                  <BarChart className="h-6 w-6 text-emerald-600 dark:text-emerald-400" />
                </div>
                <CardTitle>Continuous Optimization</CardTitle>
              </div>
              <CardDescription className="dark:text-gray-300">
                Keep improving based on real data
              </CardDescription>
            </CardHeader>
            <CardContent className="flex-grow">
              <p className="text-sm text-muted-foreground dark:text-gray-400">
                Continuously refine your recommendation strategies based on experiment results and changing customer behavior.
              </p>
            </CardContent>
          </Card>
          
          <Card className="flex flex-col items-center text-center border-none shadow-md transition-all duration-300 hover:scale-[1.02] bg-gradient-to-br from-emerald-50/50 to-primary/10 dark:from-emerald-900/10 dark:to-primary/20 dark:text-white">
            <CardHeader>
              <div className="flex flex-col items-center space-y-2">
                <div className="p-2 bg-emerald-100/50 dark:bg-emerald-800/20 rounded-full inline-flex transition-transform group-hover:scale-110">
                  <BarChartHorizontal className="h-6 w-6 text-emerald-600 dark:text-emerald-400" />
                </div>
                <CardTitle>Actionable Reports</CardTitle>
              </div>
              <CardDescription className="dark:text-gray-300">
                Clear visualization of experiment results
              </CardDescription>
            </CardHeader>
            <CardContent className="flex-grow">
              <p className="text-sm text-muted-foreground dark:text-gray-400">
                Get easy-to-understand reports that show the impact of your experiments and guide your recommendation strategy.
              </p>
            </CardContent>
          </Card>
        </div>
      </div>
    </section>
  );
};

export default Features;
