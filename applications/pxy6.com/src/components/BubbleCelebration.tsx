import React, { useEffect, useState } from "react";
import { motion } from "framer-motion";

interface BubbleProps {
  active: boolean;
  onComplete: () => void;
}

const BubbleCelebration: React.FC<BubbleProps> = ({ active, onComplete }) => {
  const [bubbles, setBubbles] = useState<Array<{ id: number; x: number; y: number; size: number; delay: number }>>([]);
  
  useEffect(() => {
    if (active) {
      // Create 30 bubbles with random properties
      const newBubbles = Array.from({ length: 30 }, (_, i) => ({
        id: i,
        x: Math.random() * 100,
        y: Math.random() * 20 + 80, // Start from bottom area
        size: Math.random() * 50 + 10,
        delay: Math.random() * 0.5,
      }));
      
      setBubbles(newBubbles);
      
      // End celebration after animation completes
      const timer = setTimeout(() => {
        onComplete();
      }, 2000);
      
      return () => clearTimeout(timer);
    }
  }, [active, onComplete]);
  
  if (!active) return null;
  
  return (
    <div className="fixed inset-0 pointer-events-none z-[100]">
      {bubbles.map((bubble) => (
        <motion.div
          key={bubble.id}
          className="absolute rounded-full bg-primary/50 dark:bg-primary/40"
          initial={{ 
            x: `${bubble.x}vw`, 
            y: `${bubble.y}vh`, 
            opacity: 0,
            scale: 0.3,
            width: bubble.size,
            height: bubble.size
          }}
          animate={{ 
            y: '-100vh', 
            opacity: [0, 0.8, 0],
            scale: [0.3, 1, 0.8]
          }}
          transition={{ 
            duration: 4 + Math.random() * 2,
            delay: bubble.delay,
            ease: "easeOut" 
          }}
        />
      ))}
    </div>
  );
};

export default BubbleCelebration;
