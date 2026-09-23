import { motion } from "framer-motion";
import { Link } from "react-router-dom";
import { Button } from "./ui/button";
import { ArrowRight, Check } from "lucide-react";

const CTASection = () => {
  return (
    <section className="py-20 px-4">
      <motion.div
        initial={{ opacity: 0, y: 30 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true }}
        transition={{ duration: 0.6 }}
        className="max-w-4xl mx-auto text-center"
      >
        <h2 className="text-3xl sm:text-4xl md:text-5xl font-bold mb-6 text-[#f8f8f8]">
          Ready to Transform Your Legal Research?
        </h2>
        <p className="text-base sm:text-xl mb-10 text-[#f8f8f8]/70 max-w-2xl mx-auto">
          Join legal professionals and citizens navigating the statutory transition with confidence.
        </p>
        
        <div className="flex flex-col sm:flex-row gap-4 justify-center">
          <Link to="/chat">
            <Button 
              size="lg" 
              className="w-full sm:w-auto h-12 sm:h-14 px-8 text-base rounded-full bg-white text-black hover:bg-gradient-to-r hover:from-purple-500 hover:to-indigo-500 hover:text-white transition-all shadow-[0_0_20px_rgba(255,255,255,0.3)] hover:shadow-[0_0_30px_rgba(168,85,247,0.5)]"
            >
              Start Legal Assistant
              <ArrowRight className="ml-2 h-5 w-5" />
            </Button>
          </Link>
          
          <Link to="/compare">
            <Button 
              variant="outline" 
              size="lg" 
              className="w-full sm:w-auto h-12 sm:h-14 px-8 text-base rounded-full border-[#f8f8f8]/20 bg-[#09090B] text-[#f8f8f8] hover:bg-[#f8f8f8]/10 hover:border-[#f8f8f8]/40"
            >
              Compare IPC vs BNS
            </Button>
          </Link>
        </div>

        <div className="mt-12 flex flex-wrap items-center justify-center gap-4 sm:gap-8 text-[#f8f8f8]/60 text-xs sm:text-sm">
          <span className="inline-flex items-center gap-1.5">
            <Check className="w-3.5 h-3.5 text-purple-400" /> Updated for 2025
          </span>
          <span className="w-1 h-1 bg-[#f8f8f8]/30 rounded-full hidden sm:inline-block" />
          <span className="inline-flex items-center gap-1.5">
            <Check className="w-3.5 h-3.5 text-purple-400" /> Verified Sources
          </span>
          <span className="w-1 h-1 bg-[#f8f8f8]/30 rounded-full hidden sm:inline-block" />
          <span className="inline-flex items-center gap-1.5">
            <Check className="w-3.5 h-3.5 text-purple-400" /> Secure & Confidential
          </span>
        </div>
      </motion.div>
    </section>
  );
};

export default CTASection;
