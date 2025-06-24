import React, { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { ArrowRight, Compass, TrendingUp, Zap, BarChart, Sparkles, Target, ShoppingBag } from "lucide-react";
import WaitingListModal from "./WaitingListModal";
import { trackHeroVariationView, trackAdVariantView } from "@/services/analyticsService";
import { getUtmParams } from "@/utils/urlUtils";

// Different hero layout variations
const HeroVariations = {
  VARIATION_A: "A", // Original layout
  VARIATION_B: "B", // Centered layout with larger metrics
  VARIATION_C: "C", // Split layout with animated metrics
};

// Ad variant content configurations
const AdVariants = {
  ad_variant_1: {
    badge: "Proven Results",
    headline: "Turn AI-Powered Hypotheses into Real Business Growth",
    metrics: [
      { value: "23.8%", label: "Upsell Success" },
      { value: "15.2%", label: "Conversion Rate" },
      { value: "9.5%", label: "Average Basket Size" }
    ],
    description: "Join pxy6 and transform your product recommendations with AI that drives measurable business growth.",
    icon: Sparkles
  },
  ad_variant_2: {
    badge: "Smart Discovery",
    headline: "Help Customers Find Their Perfect Style",
    metrics: [
      { value: "15.2%", label: "Conversion Rate" },
      { value: "23.8%", label: "Average Order Value" },
      { value: "9.5%", label: "Basket Size" }
    ],
    description: "Delight your customers with personalized style recommendations that make shopping easier and more enjoyable.",
    icon: Target
  },
  ad_variant_3: {
    badge: "Customer Success",
    headline: "Make Every Shopping Experience Count",
    metrics: [
      { value: "23.8%", label: "Average Order Value" },
      { value: "15.2%", label: "Conversion Rate" },
      { value: "9.5%", label: "Basket Size" }
    ],
    description: "Help customers discover more items they'll love, leading to happier shoppers and bigger baskets.",
    icon: ShoppingBag
  },
  ad_variant_4: {
    badge: "Style Match",
    headline: "Turn Browsers into Happy Shoppers",
    metrics: [
      { value: "15.2%", label: "Conversion Rate" },
      { value: "23.8%", label: "Average Order Value" },
      { value: "9.5%", label: "Basket Size" }
    ],
    description: "We help fashion stores create perfect style matches that customers love to buy.",
    icon: TrendingUp
  },
  ad_variant_5: {
    badge: "Smart Shopping",
    headline: "From Browsing to Buying in One Click",
    metrics: [
      { value: "77%", label: "Conversion Lift" },
      { value: "15.2%", label: "Conversion Rate" },
      { value: "23.8%", label: "Average Order Value" }
    ],
    description: "Get more customers to complete their purchase with AI-powered style recommendations they can't resist.",
    icon: Zap
  }
};

const HeroABTest = () => {
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [currentVariation, setCurrentVariation] = useState(HeroVariations.VARIATION_A);
  const [adContent, setAdContent] = useState(AdVariants.ad_variant_1);

  // Initialize A/B test variation and ad content
  useEffect(() => {
    // Check for variation in URL query parameter
    const urlParams = new URLSearchParams(window.location.search);
    const variationParam = urlParams.get('variation')?.toUpperCase();
    const adVariant = urlParams.get('utm_content');
    const noCache = urlParams.get('nocache')?.toLowerCase() === 'true';
    const utmParams = getUtmParams();
    
    // Function to get random ad variant
    const getRandomAdVariant = () => {
      const adVariants = Object.keys(AdVariants);
      return adVariants[Math.floor(Math.random() * adVariants.length)];
    };

    // Function to get random hero variation
    const getRandomHeroVariation = () => {
      const variations = Object.values(HeroVariations);
      return variations[Math.floor(Math.random() * variations.length)];
    };
    
    // Set ad content based on UTM parameter or random selection
    if (adVariant && AdVariants[adVariant]) {
      setAdContent(AdVariants[adVariant]);
      if (!noCache) {
        localStorage.setItem("adVariant", adVariant);
      }
      // Track ad variant view
      trackAdVariantView(adVariant, utmParams);
    } else {
      // Get stored ad variant or select random one
      const storedAdVariant = noCache ? null : localStorage.getItem("adVariant");
      if (storedAdVariant && AdVariants[storedAdVariant]) {
        setAdContent(AdVariants[storedAdVariant]);
        trackAdVariantView(storedAdVariant, utmParams);
      } else {
        // Randomly select an ad variant
        const randomAdVariant = getRandomAdVariant();
        if (!noCache) {
          localStorage.setItem("adVariant", randomAdVariant);
        }
        setAdContent(AdVariants[randomAdVariant]);
        trackAdVariantView(randomAdVariant, utmParams);
      }
    }
    
    // Handle hero variation selection
    if (variationParam && Object.values(HeroVariations).includes(variationParam)) {
      setCurrentVariation(variationParam);
      if (!noCache) {
        localStorage.setItem("heroVariation", variationParam);
      }
      trackHeroVariationView(variationParam);
    } else {
      const storedVariation = noCache ? null : localStorage.getItem("heroVariation");
      if (storedVariation && Object.values(HeroVariations).includes(storedVariation)) {
        setCurrentVariation(storedVariation);
        trackHeroVariationView(storedVariation);
      } else {
        const randomVariation = getRandomHeroVariation();
        if (!noCache) {
          localStorage.setItem("heroVariation", randomVariation);
        }
        setCurrentVariation(randomVariation);
        trackHeroVariationView(randomVariation);
      }
    }
  }, []);

  // Function to get variation URL
  const getVariationUrl = (variation: string) => {
    const url = new URL(window.location.href);
    url.searchParams.set('variation', variation);
    return url.toString();
  };

  // Variation A - Original Layout
  const VariationA = () => (
    <div className="grid gap-6 lg:grid-cols-[1fr_400px] lg:gap-12 xl:grid-cols-[1fr_600px]">
      <div className="flex flex-col justify-center space-y-6">
        <div className="inline-flex items-center rounded-full border px-3 py-1 text-sm transition-colors hover:bg-accent hover:text-accent-foreground">
          <adContent.icon className="mr-2 h-4 w-4 text-primary" />
          <span>{adContent.badge}</span>
        </div>
        <h1 className="text-4xl font-bold tracking-tighter sm:text-5xl xl:text-6xl/none">
          <span className="bg-clip-text text-transparent bg-gradient-to-r from-primary to-purple-600">
            {adContent.headline}
          </span>
        </h1>
        <div className="space-y-4">
          {adContent.metrics.map((metric, index) => (
            <div key={index} className="flex items-center gap-2 text-lg text-gray-600 dark:text-gray-400">
              <TrendingUp className="h-5 w-5 text-primary" />
              <span>Increase {metric.label.toLowerCase()} by up to {metric.value}*</span>
            </div>
          ))}
        </div>
        <p className="max-w-[600px] text-gray-600 md:text-xl dark:text-gray-400">
          {adContent.description}
        </p>
        <div className="text-sm text-gray-500 dark:text-gray-400 mt-2">
          * Illustrative metrics based on expected improvements
        </div>
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
                  {adContent.metrics.map((metric, index) => (
                    <div key={index} className="flex justify-between items-center">
                      <span>{metric.label}:</span>
                      <span className="font-bold text-emerald-500">+{metric.value}</span>
                    </div>
                  ))}
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
  );

  // Variation B - Centered Layout with Larger Metrics
  const VariationB = () => (
    <div className="flex flex-col items-center text-center space-y-8">
      <div className="inline-flex items-center rounded-full border px-3 py-1 text-sm transition-colors hover:bg-accent hover:text-accent-foreground">
        <adContent.icon className="mr-2 h-4 w-4 text-primary" />
        <span>{adContent.badge}</span>
      </div>
      <h1 className="text-4xl font-bold tracking-tighter sm:text-5xl xl:text-6xl/none">
        <span className="bg-clip-text text-transparent bg-gradient-to-r from-primary to-purple-600">
          {adContent.headline}
        </span>
      </h1>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-8 max-w-4xl">
        {adContent.metrics.map((metric, index) => (
          <div key={index} className="bg-white dark:bg-gray-800 p-6 rounded-xl shadow-lg">
            <div className="text-4xl font-bold text-emerald-500 mb-2 flex items-center justify-center gap-2">
              {metric.value}*
              <TrendingUp className="h-6 w-6" />
            </div>
            <div className="text-gray-600 dark:text-gray-400">{metric.label}</div>
          </div>
        ))}
      </div>
      <p className="max-w-[600px] text-gray-600 md:text-xl dark:text-gray-400">
        {adContent.description}
      </p>
      <div className="text-sm text-gray-500 dark:text-gray-400 mt-2">
        * Illustrative metrics based on expected improvements
      </div>
      <Button 
        className="inline-flex h-12 items-center justify-center rounded-md bg-primary px-8 text-base font-medium text-primary-foreground shadow transition-colors hover:bg-primary/90 focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:pointer-events-none disabled:opacity-50"
        onClick={() => setIsModalOpen(true)}
      >
        Join Waitlist
        <ArrowRight className="ml-2 h-5 w-5" />
      </Button>
    </div>
  );

  // Variation C - Split Layout with Animated Metrics
  const VariationC = () => (
    <div className="grid gap-6 lg:grid-cols-2 lg:gap-12">
      <div className="flex flex-col justify-center space-y-6">
        <div className="inline-flex items-center rounded-full border px-3 py-1 text-sm transition-colors hover:bg-accent hover:text-accent-foreground">
          <adContent.icon className="mr-2 h-4 w-4 text-primary" />
          <span>{adContent.badge}</span>
        </div>
        <h1 className="text-4xl font-bold tracking-tighter sm:text-5xl xl:text-6xl/none">
          <span className="bg-clip-text text-transparent bg-gradient-to-r from-primary to-purple-600">
            {adContent.headline}
          </span>
        </h1>
        <p className="max-w-[600px] text-gray-600 md:text-xl dark:text-gray-400">
          {adContent.description}
        </p>
        <Button 
          className="inline-flex h-12 items-center justify-center rounded-md bg-primary px-8 text-base font-medium text-primary-foreground shadow transition-colors hover:bg-primary/90 focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:pointer-events-none disabled:opacity-50"
          onClick={() => setIsModalOpen(true)}
        >
          Join Waitlist
          <ArrowRight className="ml-2 h-5 w-5" />
        </Button>
      </div>
      <div className="flex items-center justify-center">
        <div className="flex flex-col gap-4 w-full">
          <div className="grid grid-cols-2 gap-4 w-full">
            {adContent.metrics.map((metric, index) => (
              <div key={index} className="bg-white dark:bg-gray-800 p-6 rounded-xl shadow-lg transform hover:scale-105 transition-transform">
                <BarChart className="h-8 w-8 text-primary mb-4" />
                <div className="text-3xl font-bold text-emerald-500 mb-2 flex items-center gap-2">
                  {metric.value}*
                  <TrendingUp className="h-5 w-5" />
                </div>
                <div className="text-gray-600 dark:text-gray-400">{metric.label}</div>
              </div>
            ))}
            <div className="bg-white dark:bg-gray-800 p-6 rounded-xl shadow-lg transform hover:scale-105 transition-transform">
              <Compass className="h-8 w-8 text-primary mb-4" />
              <div className="text-3xl font-bold text-emerald-500 mb-2 flex items-center gap-2">
                100%*
                <TrendingUp className="h-5 w-5" />
              </div>
              <div className="text-gray-600 dark:text-gray-400">AI-Powered</div>
            </div>
          </div>
          <div className="text-sm text-gray-500 dark:text-gray-400 text-center">
            * Illustrative metrics based on expected improvements
          </div>
        </div>
      </div>
    </div>
  );

  return (
    <section className="w-full flex items-center justify-center min-h-[calc(100vh-80px)]">
      <div className="container px-4 md:px-6 py-16 md:py-20">
        {currentVariation === HeroVariations.VARIATION_A && <VariationA />}
        {currentVariation === HeroVariations.VARIATION_B && <VariationB />}
        {currentVariation === HeroVariations.VARIATION_C && <VariationC />}
      </div>
      
      {/* Waiting List Modal */}
      <WaitingListModal open={isModalOpen} onOpenChange={setIsModalOpen} />
    </section>
  );
};

export default HeroABTest; 