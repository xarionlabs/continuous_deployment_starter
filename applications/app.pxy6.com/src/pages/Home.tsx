import React from 'react';
import { Button } from "@/components/ui/button";

export const Home = () => {
  return (
    <div className="min-h-screen bg-gradient-to-b from-gray-50 to-gray-100 dark:from-gray-900 dark:to-gray-800">
      {/* Hero Section */}
      <section className="w-full py-20 md:py-32">
        <div className="container px-4 md:px-6">
          <div className="flex flex-col items-center justify-center space-y-4 text-center">
            <div className="inline-flex items-center rounded-full border px-3 py-1 text-sm">
              <span className="mr-2">🚀</span>
              Welcome to app.pxy6.com
            </div>
            <h1 className="text-4xl font-bold tracking-tighter sm:text-5xl md:text-6xl">
              Your Application is Ready
            </h1>
            <p className="mx-auto max-w-[700px] text-gray-500 md:text-xl dark:text-gray-400">
              A modern, responsive application built with React, Vite, and Tailwind CSS.
              Start building something amazing!
            </p>
            <div className="flex flex-col sm:flex-row gap-4 pt-4">
              <Button size="lg">
                Get Started
              </Button>
              <Button variant="outline" size="lg">
                Learn More
              </Button>
            </div>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section className="w-full py-12 md:py-24 bg-white dark:bg-gray-800/50">
        <div className="container px-4 md:px-6">
          <div className="flex flex-col items-center justify-center space-y-4 text-center">
            <h2 className="text-3xl font-bold tracking-tighter sm:text-4xl">
              Features
            </h2>
            <div className="grid gap-6 md:grid-cols-3 mt-8">
              <div className="rounded-lg border p-6 shadow-sm">
                <div className="h-12 w-12 rounded-full bg-primary/10 flex items-center justify-center mb-4">
                  <span className="text-primary text-xl">⚡</span>
                </div>
                <h3 className="text-xl font-bold mb-2">Fast Development</h3>
                <p className="text-gray-500 dark:text-gray-400">
                  Built with Vite for lightning fast development and hot module replacement.
                </p>
              </div>
              <div className="rounded-lg border p-6 shadow-sm">
                <div className="h-12 w-12 rounded-full bg-primary/10 flex items-center justify-center mb-4">
                  <span className="text-primary text-xl">🎨</span>
                </div>
                <h3 className="text-xl font-bold mb-2">Beautiful UI</h3>
                <p className="text-gray-500 dark:text-gray-400">
                  Styled with Tailwind CSS for beautiful, responsive designs.
                </p>
              </div>
              <div className="rounded-lg border p-6 shadow-sm">
                <div className="h-12 w-12 rounded-full bg-primary/10 flex items-center justify-center mb-4">
                  <span className="text-primary text-xl">🔧</span>
                </div>
                <h3 className="text-xl font-bold mb-2">Type Safe</h3>
                <p className="text-gray-500 dark:text-gray-400">
                  TypeScript support out of the box for better developer experience.
                </p>
              </div>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
};

export default Home;
