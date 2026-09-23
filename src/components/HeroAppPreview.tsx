import React from "react";
import { Link } from "react-router-dom";
import { 
  Scale, 
  Bot, 
  Zap, 
  Send, 
  Mic, 
  ShieldAlert, 
  AlertTriangle, 
  ShoppingBag, 
  BookOpen, 
  Check, 
  Sparkles,
  ArrowRight
} from "lucide-react";

export const HeroAppPreview: React.FC = () => {
  return (
    <div className="w-full h-full min-h-[380px] sm:min-h-[460px] md:min-h-[520px] bg-[#0c0c0e] text-white flex flex-col justify-between font-sans select-none overflow-hidden rounded-xl border border-white/5">
      {/* Top Application Window Bar */}
      <div className="border-b border-[#27272a] bg-[#141417] px-3 sm:px-5 py-2.5 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-2 sm:gap-3">
          {/* macOS window control dots */}
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-red-500/80 inline-block" />
            <span className="w-2.5 h-2.5 rounded-full bg-yellow-500/80 inline-block" />
            <span className="w-2.5 h-2.5 rounded-full bg-green-500/80 inline-block" />
          </div>
          <div className="h-3 w-px bg-white/10 hidden sm:block" />
          <div className="flex items-center gap-1.5">
            <div className="w-5 h-5 rounded-md bg-purple-500/20 border border-purple-500/30 flex items-center justify-center">
              <Scale className="w-3 h-3 text-purple-400" />
            </div>
            <span className="text-xs font-semibold text-gray-200 tracking-tight">LegalAi</span>
            <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-purple-500/10 text-purple-300 border border-purple-500/20 hidden xs:inline-block">
              BNS v2
            </span>
          </div>
        </div>

        {/* Status & Controls */}
        <div className="flex items-center gap-1.5 sm:gap-2">
          <div className="hidden sm:flex items-center gap-1 px-2 py-0.5 rounded-md bg-[#1f1f23] border border-white/5 text-[11px] text-gray-400">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
            <span>NVIDIA NIM</span>
          </div>
          <div className="flex items-center gap-1 bg-[#1f1f23] p-0.5 rounded-md border border-white/5">
            <span className="flex items-center gap-1 px-2 py-0.5 text-[11px] font-medium rounded bg-purple-500/15 text-purple-300 border border-purple-500/20">
              <Zap className="w-2.5 h-2.5" /> Args
            </span>
            <span className="flex items-center gap-1 px-2 py-0.5 text-[11px] font-medium rounded bg-blue-500/15 text-blue-300 border border-blue-500/20">
              <Scale className="w-2.5 h-2.5" /> Analysis
            </span>
          </div>
        </div>
      </div>

      {/* Chat Messages Body */}
      <div className="flex-1 p-3 sm:p-5 overflow-y-auto space-y-3 sm:space-y-4">
        {/* User Query */}
        <div className="flex justify-end">
          <div className="max-w-[90%] sm:max-w-[75%] rounded-2xl rounded-br-sm px-3.5 sm:px-4 py-2 sm:py-2.5 bg-[#27272a] border border-white/10 text-white text-xs sm:text-sm leading-relaxed shadow-sm">
            What is the punishment for murder under BNS Section 103?
          </div>
        </div>

        {/* AI Assistant Answer */}
        <div className="flex items-start gap-2.5 sm:gap-3">
          <div className="w-6 h-6 sm:w-7 sm:h-7 rounded-lg bg-gradient-to-br from-purple-500/20 to-blue-500/20 border border-purple-500/30 flex items-center justify-center shrink-0 mt-1">
            <Bot className="w-3.5 h-3.5 text-purple-400" />
          </div>
          <div className="flex-1 max-w-[95%] sm:max-w-[85%] space-y-2.5">
            <div className="rounded-2xl rounded-tl-sm p-3.5 sm:p-4 bg-[#141417] border border-white/10 text-gray-200 text-xs sm:text-sm leading-relaxed space-y-2">
              <p className="font-medium text-white">
                Under <span className="text-purple-300 font-semibold">Section 103(1) of Bharatiya Nyaya Sanhita, 2023</span> (replacing Section 302 IPC):
              </p>
              <div className="pl-3 border-l-2 border-purple-500/40 text-gray-300 space-y-1 text-[11px] sm:text-xs">
                <p>• <strong>Primary Punishment:</strong> Punishable with <strong>death or imprisonment for life</strong>, with mandatory fine.</p>
                <p>• <strong>Legislative Shift:</strong> Section 103(2) specifically introduces stringent penal provisions for murder committed by mob or groups.</p>
              </div>

              {/* Citations Pill Bar */}
              <div className="pt-2 flex flex-wrap items-center gap-1.5 sm:gap-2">
                <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-purple-500/10 border border-purple-500/20 text-purple-300 text-[10px] sm:text-[11px]">
                  <BookOpen className="w-3 h-3" /> BNS Section 103(1)
                </span>
                <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-blue-500/10 border border-blue-500/20 text-blue-300 text-[10px] sm:text-[11px]">
                  <Check className="w-3 h-3" /> Replaces IPC 302
                </span>
                <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-300 text-[10px] sm:text-[11px] hidden xs:inline-flex">
                  AIR 1980 SC 898
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Quick Prompts Bar inside Mockup */}
        <div className="pt-1">
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
            <div className="p-2 sm:p-2.5 rounded-lg bg-[#18181b] border border-white/5 flex items-center justify-between gap-2 hover:border-purple-500/30 transition-all cursor-pointer">
              <div className="flex items-center gap-2 min-w-0">
                <div className="p-1 rounded bg-purple-500/10 text-purple-400 shrink-0">
                  <ShieldAlert className="w-3 h-3" />
                </div>
                <span className="text-[11px] sm:text-xs text-gray-300 truncate">Murder Provisions</span>
              </div>
              <span className="text-[9px] font-mono text-gray-400 bg-white/5 px-1 py-0.5 rounded shrink-0">BNS §103</span>
            </div>

            <div className="p-2 sm:p-2.5 rounded-lg bg-[#18181b] border border-white/5 flex items-center justify-between gap-2 hover:border-amber-500/30 transition-all cursor-pointer">
              <div className="flex items-center gap-2 min-w-0">
                <div className="p-1 rounded bg-amber-500/10 text-amber-400 shrink-0">
                  <AlertTriangle className="w-3 h-3" />
                </div>
                <span className="text-[11px] sm:text-xs text-gray-300 truncate">Cheating & Fraud</span>
              </div>
              <span className="text-[9px] font-mono text-gray-400 bg-white/5 px-1 py-0.5 rounded shrink-0">BNS §318</span>
            </div>

            <div className="p-2 sm:p-2.5 rounded-lg bg-[#18181b] border border-white/5 flex items-center justify-between gap-2 hover:border-blue-500/30 transition-all cursor-pointer hidden sm:flex">
              <div className="flex items-center gap-2 min-w-0">
                <div className="p-1 rounded bg-blue-500/10 text-blue-400 shrink-0">
                  <ShoppingBag className="w-3 h-3" />
                </div>
                <span className="text-[11px] sm:text-xs text-gray-300 truncate">Consumer Rights</span>
              </div>
              <span className="text-[9px] font-mono text-gray-400 bg-white/5 px-1 py-0.5 rounded shrink-0">CPA §35</span>
            </div>
          </div>
        </div>
      </div>

      {/* Bottom Mock Input Bar */}
      <div className="p-2.5 sm:p-3.5 border-t border-[#27272a] bg-[#141417]/90 backdrop-blur-sm shrink-0">
        <div className="flex items-center gap-2 rounded-xl bg-[#0c0c0e] border border-white/10 px-3 py-2 text-xs sm:text-sm text-gray-400 shadow-inner">
          <Mic className="w-4 h-4 text-gray-400 shrink-0 hover:text-purple-400 transition-colors" />
          <span className="flex-1 truncate text-gray-400 text-[11px] sm:text-xs">
            Ask any legal question in English or Hindi...
          </span>
          <Link
            to="/chat"
            className="w-7 h-7 rounded-lg bg-white text-black hover:bg-purple-300 transition-all flex items-center justify-center shrink-0 shadow-sm"
            aria-label="Try Legal Assistant"
          >
            <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        </div>
      </div>
    </div>
  );
};
