import { useState, useRef, useEffect } from "react";
import { useToast } from "@/components/ui/use-toast";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import { Loader2, Scale, Zap, BookOpen, Mic, MicOff, Download, Sparkles, Send, Menu, Plus, Trash2, MessageSquare, ExternalLink, Volume2, VolumeX, ShieldAlert, ShoppingBag, AlertTriangle, FileText } from "lucide-react";
import Header from "@/components/Header";
import ReactMarkdown from "react-markdown";
import { motion, AnimatePresence } from "framer-motion";
import { cn } from "@/lib/utils";
import { ReadAloudButton } from "@/components/ReadAloudButton";
import { getApiUrl } from "@/lib/api";

import jsPDF from "jspdf";
import autoTable from "jspdf-autotable";

interface Judgment {
    title: string;
    summary: string;
}

interface Arguments {
    for: string[];
    against: string[];
}

interface NeutralAnalysis {
    factors: string[];
    interpretations: string[];
}

interface Message {
    role: 'user' | 'assistant';
    content: string;
    judgments?: Judgment[];
    arguments?: Arguments;
    neutral_analysis?: NeutralAnalysis;
    citations?: any[];
}

const QUICK_PROMPTS = [
    { label: "Punishment for Murder", query: "Punishment for murder under BNS", tag: "BNS §103", icon: ShieldAlert },
    { label: "File Consumer Complaint", query: "How to file a consumer complaint", tag: "Consumer Act", icon: ShoppingBag },
    { label: "Check Cheating Laws", query: "Punishment for cheating", tag: "BNS §318", icon: AlertTriangle },
    { label: "Draft Rent Agreement", query: "Essentials of a rent agreement", tag: "Contracts", icon: FileText }
];

const LOADING_TEXTS = [
    "Scanning BNS Section 103...",
    "Cross-referencing Judgments...",
    "Analyzing IPC vs BNS...",
    "Verifying Legal Precedents...",
    "Synthesizing Neutral Analysis..."
];

const ChatPage = () => {
  const { toast } = useToast();
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [language, setLanguage] = useState<'en' | 'hi'>('en');
  const [domain, setDomain] = useState("all");
  const [argumentsMode, setArgumentsMode] = useState(false);
  const [analysisMode, setAnalysisMode] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [isListening, setIsListening] = useState(false);
  const [loadingText, setLoadingText] = useState(LOADING_TEXTS[0]);
  const scrollRef = useRef<HTMLDivElement>(null);

  // Conversation history state
  const [conversations, setConversations] = useState<Array<{
    id: string;
    title: string;
    messages: Message[];
    timestamp: number;
  }>>([]);
  const [activeConversationId, setActiveConversationId] = useState<string | null>(null);
  const [sidebarOpen, setSidebarOpen] = useState<boolean>(() => {
    if (typeof window !== 'undefined') {
      return window.innerWidth >= 768;
    }
    return false;
  });

  // Text-to-speech state
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [speakingMessageIndex, setSpeakingMessageIndex] = useState<number | null>(null);
  const speechSynthesisRef = useRef<SpeechSynthesisUtterance | null>(null);

  // Load conversations from localStorage on mount
  useEffect(() => {
    const saved = localStorage.getItem('legal-compass-conversations');
    if (saved) {
      try {
        const parsed = JSON.parse(saved);
        setConversations(parsed);
        // Load the most recent conversation
        if (parsed.length > 0) {
          const latest = parsed[0];
          setActiveConversationId(latest.id);
          setMessages(latest.messages);
        }
      } catch (e) {
        console.error('Failed to load conversations:', e);
      }
    }
  }, []);

  // Save conversations to localStorage whenever they change
  useEffect(() => {
    if (conversations.length > 0) {
      localStorage.setItem('legal-compass-conversations', JSON.stringify(conversations));
    }
  }, [conversations]);

  // Cleanup speech synthesis on unmount
  useEffect(() => {
    return () => {
      if (speechSynthesisRef.current) {
        window.speechSynthesis.cancel();
      }
    };
  }, []);

  // Text-to-speech helper to strip raw markdown and URLs for natural speaking
  const cleanSpeechText = (rawText: string) => {
    return rawText
      .replace(/https?:\/\/\S+/gi, '') // Strip URLs
      .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1') // [Text](URL) -> Text
      .replace(/#{1,6}\s/g, '') // Strip headers
      .replace(/\*\*([^*]+)\*\*/g, '$1') // Bold
      .replace(/\*([^*]+)\*/g, '$1') // Italic
      .replace(/`([^`]+)`/g, '$1') // Code
      .replace(/^[-*•]\s+/gm, '') // Bullet points
      .replace(/\|.*?\|/g, '') // Tables
      .replace(/\n+/g, '. ') // Paragraphs to full stops for natural speech rhythm
      .trim();
  };

  // Text-to-speech functions
  const handleReadAloud = (rawText: string, messageIndex: number) => {
    // Check browser support
    if (!('speechSynthesis' in window)) {
      alert('Text-to-speech is not supported in your browser. Please use Chrome, Edge, or Safari.');
      return;
    }

    // If already speaking this message, stop it
    if (isSpeaking && speakingMessageIndex === messageIndex) {
      window.speechSynthesis.cancel();
      setIsSpeaking(false);
      setSpeakingMessageIndex(null);
      return;
    }

    // Stop any ongoing speech
    window.speechSynthesis.cancel();
    const textToSpeak = cleanSpeechText(rawText);
    if (!textToSpeak) return;

    // Small delay to prevent interruption error
    setTimeout(() => {
      // Get available voices
      let voices = window.speechSynthesis.getVoices();
      
      // If voices aren't loaded yet, wait for them
      if (voices.length === 0) {
        window.speechSynthesis.onvoiceschanged = () => {
          voices = window.speechSynthesis.getVoices();
          startSpeaking(voices);
        };
      } else {
        startSpeaking(voices);
      }

      function startSpeaking(voices: SpeechSynthesisVoice[]) {
        const utterance = new SpeechSynthesisUtterance(textToSpeak);
        
        // Select female or natural English voice
        const naturalVoice = voices.find(
          voice => voice.name.includes('Natural') ||
                   voice.name.includes('Google') ||
                   voice.name.includes('Samantha') || 
                   voice.name.includes('Zira') ||
                   voice.name.includes('Female')
        ) || voices.find(voice => voice.lang.startsWith(language === 'hi' ? 'hi' : 'en'));

        if (naturalVoice) {
          utterance.voice = naturalVoice;
        }

        utterance.rate = 0.9;
        utterance.pitch = 1.05;
        utterance.volume = 1.0;

        // Event handlers
        utterance.onstart = () => {
          setIsSpeaking(true);
          setSpeakingMessageIndex(messageIndex);
        };

        utterance.onend = () => {
          setIsSpeaking(false);
          setSpeakingMessageIndex(null);
        };

        utterance.onerror = (event) => {
          console.error('Speech synthesis error:', event);
          setIsSpeaking(false);
          setSpeakingMessageIndex(null);
        };

        speechSynthesisRef.current = utterance;
        window.speechSynthesis.speak(utterance);
      }
    }, 100);
  };

  useEffect(() => {
    if (scrollRef.current) {
        scrollRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages, isLoading]);

  useEffect(() => {
    let interval: NodeJS.Timeout;
    if (isLoading) {
        let i = 0;
        interval = setInterval(() => {
            i = (i + 1) % LOADING_TEXTS.length;
            setLoadingText(LOADING_TEXTS[i]);
        }, 800);
    }
    return () => clearInterval(interval);
  }, [isLoading]);

  const startListening = () => {
    if ('webkitSpeechRecognition' in window) {
      const recognition = new (window as any).webkitSpeechRecognition();
      recognition.lang = language === 'hi' ? 'hi-IN' : 'en-US';
      recognition.continuous = false;
      recognition.interimResults = false;

      recognition.onstart = () => setIsListening(true);
      recognition.onend = () => setIsListening(false);
      recognition.onresult = (event: any) => {
        const transcript = event.results[0][0].transcript;
        setInput(transcript);
      };
      
      recognition.start();
    } else {
      alert("Voice input is not supported in this browser.");
    }
  };  const getKanoonLink = (source?: string, section?: string, directUrl?: string) => {
    if (directUrl && (directUrl.startsWith("http://") || directUrl.startsWith("https://"))) {
      return directUrl;
    }
    const cleanSource = (source || "")
      .replace(/^Statute$/i, "")
      .replace(/null|undefined/gi, "")
      .trim();
    const cleanSection = (section || "")
      .replace(/Section\s+Section/gi, "Section")
      .replace(/null|undefined/gi, "")
      .trim();
    const query = [cleanSource, cleanSection].filter(Boolean).join(" ");
    return `https://indiankanoon.org/search/?formInput=${encodeURIComponent(query || "Indian Law Statute")}`;
  };

  const cleanPdfText = (text: string) => {
    return text
      .replace(/https?:\/\/\S+/gi, '') // Strip URLs
      .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1') // [Text](URL) -> Text
      .replace(/\*\*([^*]+)\*\*/g, '$1') // Bold
      .replace(/\*([^*]+)\*/g, '$1')     // Italic
      .replace(/#{1,6}\s/g, '')          // Headings
      .replace(/`([^`]+)`/g, '$1')       // Inline code
      .replace(/^[-*•]\s+/gm, '• ')      // Normalize bullets
      .replace(/\r\n/g, '\n')
      .replace(/\n{3,}/g, '\n\n')
      .trim();
  };

  const exportPDF = (msg: Message, queryTitle: string) => {
    try {
      const doc = new jsPDF();
      const pageHeight = doc.internal.pageSize.height;
      const pageWidth = doc.internal.pageSize.width;
      
      // Top Header Banner
      doc.setFillColor(18, 18, 22);
      doc.rect(0, 0, pageWidth, 28, 'F');
      
      doc.setFontSize(16);
      doc.setTextColor(255, 255, 255);
      doc.text("LegalAi Research Report", 15, 18);
      
      doc.setFontSize(9);
      doc.setTextColor(180, 180, 190);
      doc.text(`Date: ${new Date().toLocaleDateString()} | Domain: ${domain.toUpperCase()}`, 15, 24);
      
      let yPos = 36;
      
      // Query Box
      doc.setFillColor(245, 245, 248);
      doc.roundedRect(15, yPos, pageWidth - 30, 14, 2, 2, 'F');
      doc.setFontSize(10);
      doc.setTextColor(40, 40, 50);
      doc.text(`Query: ${queryTitle || "Indian Legal Research"}`, 18, yPos + 9);
      yPos += 22;
      
      // Content with safe line-by-line pagination
      doc.setFontSize(10);
      doc.setTextColor(30, 30, 30);
      const cleaned = cleanPdfText(msg.content);
      const splitText = doc.splitTextToSize(cleaned, 180);
      const lineHeight = 5.5;
      
      splitText.forEach((line: string) => {
        if (yPos > pageHeight - 25) {
          doc.addPage();
          yPos = 20;
        }
        doc.text(line, 15, yPos);
        yPos += lineHeight;
      });
      
      // Citations Table
      if (msg.citations && msg.citations.length > 0) {
        if (yPos > pageHeight - 50) {
          doc.addPage();
          yPos = 20;
        } else {
          yPos += 8;
        }
        
        doc.setFontSize(12);
        doc.setTextColor(30, 30, 40);
        doc.text("Statutory Citations & Precedents", 15, yPos);
        yPos += 6;
        
        const citationData = msg.citations.map(c => [
          c.source || "Statute",
          (c.section || "").replace(/null/gi, "Provision"),
          (c.text || "").replace(/---/g, "").slice(0, 140)
        ]);
        
        autoTable(doc, {
          startY: yPos,
          head: [['Source', 'Section', 'Summary']],
          body: citationData,
          theme: 'grid',
          headStyles: { fillColor: [40, 35, 60] },
          styles: { fontSize: 8 }
        });
      }
      
      // Footer across all generated pages
      const totalPages = doc.getNumberOfPages();
      for (let i = 1; i <= totalPages; i++) {
        doc.setPage(i);
        doc.setFontSize(8);
        doc.setTextColor(130, 130, 140);
        doc.text(`LegalAi Research Report • Page ${i} of ${totalPages} • Informational only`, pageWidth / 2, pageHeight - 10, { align: 'center' });
      }
      
      doc.save(`LegalAi_Report_${Date.now()}.pdf`);
      toast({
        title: "Report Exported",
        description: "PDF report downloaded successfully."
      });
    } catch (err: any) {
      console.error("PDF export error:", err);
      toast({
        title: "Export Failed",
        description: "Could not generate PDF. Please try again.",
        variant: "destructive"
      });
    }
  };

  const exportFullChat = () => {
    try {
      const doc = new jsPDF();
      const pageHeight = doc.internal.pageSize.height;
      const pageWidth = doc.internal.pageSize.width;
      
      // Header Banner
      doc.setFillColor(18, 18, 22);
      doc.rect(0, 0, pageWidth, 28, 'F');
      
      doc.setFontSize(16);
      doc.setTextColor(255, 255, 255);
      doc.text("LegalAi Conversation History", 15, 18);
      
      doc.setFontSize(9);
      doc.setTextColor(180, 180, 190);
      doc.text(`Date: ${new Date().toLocaleDateString()} | Domain: ${domain.toUpperCase()} | Messages: ${messages.length}`, 15, 24);
      
      let yPos = 38;
      const lineHeight = 5.5;
      
      messages.forEach((msg) => {
        if (yPos > pageHeight - 35) {
          doc.addPage();
          yPos = 20;
        }
        
        // Sender Label
        doc.setFontSize(11);
        if (msg.role === 'user') {
          doc.setTextColor(30, 80, 180);
          doc.text("You:", 15, yPos);
        } else {
          doc.setTextColor(120, 40, 180);
          doc.text("LegalAi Assistant:", 15, yPos);
        }
        yPos += 6;
        
        // Message Content
        doc.setFontSize(10);
        doc.setTextColor(40, 40, 40);
        const cleanContent = cleanPdfText(msg.content);
        const splitText = doc.splitTextToSize(cleanContent, 180);
        
        splitText.forEach((line: string) => {
          if (yPos > pageHeight - 25) {
            doc.addPage();
            yPos = 20;
          }
          doc.text(line, 15, yPos);
          yPos += lineHeight;
        });
        
        yPos += 4;
        doc.setDrawColor(230, 230, 235);
        doc.line(15, yPos, 195, yPos);
        yPos += 8;
      });
      
      const totalPages = doc.getNumberOfPages();
      for (let i = 1; i <= totalPages; i++) {
        doc.setPage(i);
        doc.setFontSize(8);
        doc.setTextColor(130, 130, 140);
        doc.text(`LegalAi Conversation Transcript • Page ${i} of ${totalPages}`, pageWidth / 2, pageHeight - 10, { align: 'center' });
      }
      
      doc.save(`LegalAi_Chat_${Date.now()}.pdf`);
      toast({
        title: "Chat Exported",
        description: "Complete chat history downloaded as PDF."
      });
    } catch (err: any) {
      console.error("Full chat export error:", err);
      toast({
        title: "Export Failed",
        description: "Could not export chat history.",
        variant: "destructive"
      });
    }
  };

  // Conversation management functions
  const createNewChat = () => {
    setMessages([]);
    setActiveConversationId(null);
    setInput("");
  };

  const switchConversation = (convId: string) => {
    const conv = conversations.find(c => c.id === convId);
    if (conv) {
      setActiveConversationId(conv.id);
      setMessages(conv.messages);
    }
  };

  const deleteConversation = (convId: string) => {
    setConversations(prev => prev.filter(c => c.id !== convId));
    if (activeConversationId === convId) {
      createNewChat();
    }
  };

  const saveCurrentConversation = (updatedMessages: Message[]) => {
    if (updatedMessages.length === 0) return;

    const title = updatedMessages[0].content.slice(0, 40) + (updatedMessages[0].content.length > 40 ? '...' : '');
    const timestamp = Date.now();

    if (activeConversationId) {
      // Update existing conversation
      setConversations(prev => prev.map(c => 
        c.id === activeConversationId 
          ? { ...c, messages: updatedMessages, timestamp }
          : c
      ));
    } else {
      // Create new conversation
      const newId = `conv_${timestamp}`;
      setActiveConversationId(newId);
      setConversations(prev => [{
        id: newId,
        title,
        messages: updatedMessages,
        timestamp
      }, ...prev]);
    }
  };

  const handleSend = async (text = input) => {
    if (!text.trim()) return;
    
    const userMsg: Message = { role: 'user', content: text };
    setMessages(prev => [...prev, userMsg]);
    setInput("");
    setIsLoading(true);

    // Auto-detect language based on input script
    // If Devanagari characters are present, switch to Hindi. Otherwise, default to English.
    const isHindiInput = /[\u0900-\u097F]/.test(text);
    const useLanguage = isHindiInput ? 'hi' : 'en';
    
    // Update local state to reflect the change visually
    if (useLanguage !== language) {
        setLanguage(useLanguage);
    }

    try {
        const response = await fetch(getApiUrl('/query'), { // Pointing directly to backend for stability
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                query: text, 
                language: useLanguage, // Use determined language immediately 
                domain, 
                arguments_mode: argumentsMode,
                analysis_mode: analysisMode 
            })
        });
        
        const data = await response.json();
        
        if (data.answer) {
            const newMessages = [...messages, userMsg, { 
                role: 'assistant' as const, 
                content: data.answer,
                judgments: data.related_judgments,
                arguments: data.arguments,
                neutral_analysis: data.neutral_analysis,
                citations: data.citations
            }];
            setMessages(newMessages);
            saveCurrentConversation(newMessages);
        } else {
             const newMessages = [...messages, userMsg, { role: 'assistant' as const, content: "Sorry, I couldn't process that request." }];
             setMessages(newMessages);
             saveCurrentConversation(newMessages);
        }
    } catch (error) {
        console.error("Chat Error:", error);
        const newMessages = [...messages, userMsg, { role: 'assistant' as const, content: "Error connecting to the server. Please ensure the backend is running." }];
        setMessages(newMessages);
        saveCurrentConversation(newMessages);
    } finally {
        setIsLoading(false);
    }
  };

  return (
    <div className="h-screen flex flex-col bg-[#09090b] text-white selection:bg-purple-500/30 font-sans">
      <Header autoHide />
      
      {/* Main Layout Container */}
      <div className="flex-1 flex overflow-hidden pt-0 relative">
        
        {/* Mobile Backdrop */}
        {sidebarOpen && (
          <div 
            onClick={() => setSidebarOpen(false)}
            className="fixed inset-0 bg-black/70 backdrop-blur-sm z-30 md:hidden transition-opacity"
            aria-label="Close sidebar"
          />
        )}

        {/* Sidebar */}
        <AnimatePresence mode="wait">
          {sidebarOpen && (
            <motion.aside
              initial={{ x: -280, opacity: 0 }}
              animate={{ x: 0, opacity: 1 }}
              exit={{ x: -280, opacity: 0 }}
              transition={{ type: "spring", stiffness: 300, damping: 30 }}
              className="fixed md:static inset-y-0 left-0 w-[270px] bg-[#0c0c0e] border-r border-[#27272a] flex flex-col shrink-0 z-40 h-full shadow-2xl md:shadow-none"
            >
              <div className="p-3">
                <Button
                  onClick={createNewChat}
                  className="w-full justify-start gap-2 bg-transparent hover:bg-[#27272a] text-sm font-medium text-gray-200 border border-[#27272a] h-10 px-3 transition-all"
                >
                  <Plus className="w-4 h-4" />
                  New Chat
                </Button>
              </div>

               <div className="flex-1 overflow-y-auto px-2 py-2 no-scrollbar">
                 {conversations.length > 0 && (
                   <div className="mb-4">
                     <h3 className="px-3 py-2 text-xs font-semibold text-gray-500 uppercase tracking-wider">Recent</h3>
                     <div className="space-y-0.5">
                       {conversations.map((conv) => (
                         <div
                           key={conv.id}
                           onClick={() => {
                             switchConversation(conv.id);
                             if (window.innerWidth < 768) setSidebarOpen(false);
                           }}
                           className={cn(
                             "group relative flex items-center gap-2 px-3 py-2.5 rounded-md cursor-pointer transition-colors text-sm",
                             activeConversationId === conv.id 
                               ? "bg-[#27272a] text-white" 
                               : "text-gray-400 hover:bg-[#18181b] hover:text-gray-200"
                           )}
                         >
                           <MessageSquare className="w-4 h-4 shrink-0 opacity-70" />
                           <span className="flex-1 truncate font-normal">
                             {conv.title}
                           </span>
                           <Button
                             variant="ghost"
                             size="icon"
                             className="h-6 w-6 opacity-0 group-hover:opacity-100 -mr-1 hover:bg-white/10"
                             onClick={(e) => {
                               e.stopPropagation();
                               deleteConversation(conv.id);
                             }}
                           >
                             <Trash2 className="h-3.5 w-3.5 text-gray-400 hover:text-red-400" />
                           </Button>
                         </div>
                       ))}
                     </div>
                   </div>
                 )}
               </div>
            </motion.aside>
          )}
        </AnimatePresence>

        {/* Main Chat Area */}
        <main className="flex-1 flex flex-col relative min-w-0 bg-[#09090b]">
           {/* Mobile Sidebar Toggle */}
           {!sidebarOpen && (
             <Button
               variant="ghost"
               size="icon"
               onClick={() => setSidebarOpen(true)}
               className="absolute top-3 left-3 z-20 text-gray-400 hover:text-white hover:bg-[#27272a] md:hidden"
             >
               <Menu className="h-5 w-5" />
             </Button>
           )}

           {/* Top Controls Bar */}
           <div className="w-full border-b border-[#27272a] px-3 sm:px-6 py-2.5 sm:py-3 flex items-center justify-between sm:justify-end gap-2 sm:gap-3 bg-[#09090b]/80 backdrop-blur-sm z-10 overflow-x-auto no-scrollbar">
               {sidebarOpen ? (
                 <Button
                   variant="ghost"
                   size="icon"
                   onClick={() => setSidebarOpen(false)}
                   className="mr-auto text-gray-400 hover:text-white hidden md:inline-flex"
                 >
                   <Menu className="h-5 w-5" />
                 </Button>
               ) : (
                 <Button
                   variant="ghost"
                   size="icon"
                   onClick={() => setSidebarOpen(true)}
                   className="mr-auto text-gray-400 hover:text-white hidden md:inline-flex"
                 >
                   <Menu className="h-5 w-5" />
                 </Button>
               )}
               
               <div className="flex items-center gap-1 bg-[#18181b] p-1 rounded-lg border border-[#27272a] shrink-0">
                  <Button 
                    variant="ghost" 
                    size="sm" 
                    onClick={() => setArgumentsMode(!argumentsMode)}
                    className={cn("h-7 px-2.5 sm:px-3 text-xs rounded-md transition-all", argumentsMode ? "bg-purple-500/10 text-purple-400 font-medium" : "text-gray-400 hover:text-white")}
                  >
                     <Zap className="w-3 h-3 mr-1.5" /> Args
                  </Button>
                  <Button 
                    variant="ghost" 
                    size="sm" 
                    onClick={() => setAnalysisMode(!analysisMode)}
                    className={cn("h-7 px-2.5 sm:px-3 text-xs rounded-md transition-all", analysisMode ? "bg-blue-500/10 text-blue-400 font-medium" : "text-gray-400 hover:text-white")}
                  >
                     <Scale className="w-3 h-3 mr-1.5" /> Analysis
                  </Button>
               </div>

               <div className="h-4 w-px bg-[#27272a] shrink-0" />

               {/* Language Toggle */}
               <div className="flex items-center gap-1 bg-[#18181b] p-1 rounded-lg border border-[#27272a] shrink-0">
                   <Button 
                     variant="ghost" 
                     size="sm" 
                     onClick={() => setLanguage('en')}
                     className={cn("h-7 w-7 p-0 text-xs rounded-md transition-all", language === 'en' ? "bg-white/10 text-white font-bold" : "text-gray-500 hover:text-white")}
                   >
                      EN
                   </Button>
                   <Button 
                     variant="ghost" 
                     size="sm" 
                     onClick={() => setLanguage('hi')}
                     className={cn("h-7 w-7 p-0 text-xs rounded-md transition-all", language === 'hi' ? "bg-white/10 text-white font-bold" : "text-gray-500 hover:text-white")}
                   >
                      HI
                   </Button>
               </div>
               
               <div className="h-4 w-px bg-[#27272a] shrink-0" />

               <Button 
                   variant="ghost" 
                   size="sm"
                   onClick={exportFullChat}
                   disabled={messages.length === 0}
                   className="text-gray-400 hover:text-white shrink-0"
                   title="Export Full Chat to PDF"
                >
                   <Download className="w-4 h-4" />
                </Button>

                <div className="h-4 w-px bg-[#27272a] shrink-0 hidden sm:block" />

               <Select value={domain} onValueChange={setDomain}>
                   <SelectTrigger className="w-[110px] sm:w-[130px] h-8 bg-transparent border-none text-xs text-gray-300 focus:ring-0 shrink-0">
                       <SelectValue placeholder="Domain" />
                   </SelectTrigger>
                   <SelectContent className="bg-[#18181b] border-[#27272a] text-gray-300">
                       <SelectItem value="all">All Domains</SelectItem>
                       <SelectItem value="criminal">Criminal Law</SelectItem>
                       <SelectItem value="corporate">Corporate Law</SelectItem>
                   </SelectContent>
               </Select>
           </div>

           {/* Messages List */}
           <div className="flex-1 overflow-y-auto p-3 sm:p-6 scroll-smooth">
              <div className="max-w-3xl mx-auto space-y-6 pb-4">
                  <AnimatePresence mode="popLayout">
                      {messages.length === 0 && (
                          <motion.div 
                              initial={{ opacity: 0, scale: 0.95 }}
                              animate={{ opacity: 1, scale: 1 }}
                              className="min-h-[55vh] flex flex-col items-center justify-center text-center px-4"
                          >
                              <div className="w-14 h-14 sm:w-16 sm:h-16 bg-[#18181b] rounded-2xl flex items-center justify-center mb-5 border border-[#27272a] shadow-xl">
                                  <Sparkles className="w-7 h-7 sm:w-8 sm:h-8 text-purple-400" />
                              </div>
                              <h2 className="text-xl sm:text-2xl font-semibold text-white mb-2">LegalAi Research</h2>
                              <p className="text-gray-400 max-w-sm mb-8 text-xs sm:text-sm leading-relaxed">
                                  Your advanced legal intelligence assistant. Ask questions, compare statutes, or verify case citations.
                              </p>
                              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 w-full max-w-xl">
                                  {QUICK_PROMPTS.map((prompt, idx) => {
                                      const PromptIcon = prompt.icon;
                                      return (
                                          <button 
                                              key={idx}
                                              onClick={() => handleSend(prompt.query)}
                                              className="text-left p-3.5 rounded-xl bg-[#141416] border border-[#27272a] hover:bg-[#1e1e22] hover:border-purple-500/40 transition-all group flex items-start gap-3"
                                          >
                                              <div className="p-2 rounded-lg bg-purple-500/10 border border-purple-500/20 text-purple-400 group-hover:scale-105 transition-transform shrink-0 mt-0.5">
                                                  <PromptIcon className="w-4 h-4" />
                                              </div>
                                              <div className="flex-1 min-w-0">
                                                  <div className="flex items-center justify-between gap-1 mb-1">
                                                      <span className="text-sm font-medium text-gray-200 group-hover:text-white transition-colors truncate">
                                                          {prompt.label}
                                                      </span>
                                                      <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-white/5 text-gray-400 border border-white/5 shrink-0">
                                                          {prompt.tag}
                                                      </span>
                                                  </div>
                                                  <p className="text-xs text-gray-500 truncate group-hover:text-gray-400 transition-colors">
                                                      {prompt.query}
                                                  </p>
                                              </div>
                                          </button>
                                      );
                                  })}
                              </div>
                          </motion.div>
                      )}

                      {messages.map((msg, idx) => (
                          <motion.div 
                              key={idx}
                              initial={{ opacity: 0, y: 10 }}
                              animate={{ opacity: 1, y: 0 }}
                              className={cn("flex w-full gap-4", msg.role === 'user' ? "justify-end" : "justify-start")}
                          >
                              {msg.role === 'assistant' && (
                                <div className="w-8 h-8 rounded-full bg-purple-600/20 flex items-center justify-center shrink-0 border border-purple-500/20 mt-1">
                                  <Scale className="w-4 h-4 text-purple-400" />
                                </div>
                              )}
                              
                              <div className={cn(
                                  "max-w-[85%] sm:max-w-[75%] rounded-2xl px-5 py-3.5 text-sm leading-relaxed",
                                  msg.role === 'user' 
                                      ? "bg-[#27272a] text-white rounded-br-none" 
                                      : "bg-transparent text-gray-200 pl-0 pt-1" // Minimal assistant look
                              )}>
                                  {msg.role === 'assistant' ? (
                                      <div className="prose prose-invert prose-sm max-w-none prose-p:leading-relaxed prose-pre:bg-[#18181b] prose-pre:border prose-pre:border-[#27272a]">
                                          <ReactMarkdown>{msg.content}</ReactMarkdown>
                                           
                                           {/* Read Aloud Button */}
                                           <div className="mt-3 flex items-center gap-2 not-prose">
                                             <Button
                                               variant="ghost"
                                               size="sm"
                                               onClick={() => handleReadAloud(msg.content, idx)}
                                               className="h-8 px-3 text-xs text-gray-400 hover:text-white hover:bg-[#27272a] transition-colors"
                                             >
                                               {isSpeaking && speakingMessageIndex === idx ? (
                                                 <>
                                                   <VolumeX className="w-3.5 h-3.5 mr-1.5" />
                                                   Stop Reading
                                                 </>
                                               ) : (
                                                 <>
                                                   <Volume2 className="w-3.5 h-3.5 mr-1.5" />
                                                   Read Aloud
                                                 </>
                                               )}
                                             </Button>
                                           </div>
                                           
                                           {/* Analysis Cards */}
                                          {(msg.neutral_analysis || msg.arguments || (msg.judgments && msg.judgments.length > 0)) && (
                                             <div className="mt-6 flex flex-col gap-4 not-prose">
                                                {msg.neutral_analysis && (
                                                    <div className="bg-blue-900/10 border border-blue-800/20 rounded-lg p-4">
                                                        <h4 className="flex items-center gap-2 text-blue-400 font-medium mb-3 text-xs uppercase tracking-wider">
                                                            Neutral Analysis
                                                        </h4>
                                                        <div className="grid md:grid-cols-2 gap-4">
                                                           <ul className="text-xs text-blue-200/70 list-disc list-inside space-y-1">
                                                               {msg.neutral_analysis.factors.map((f, i) => <li key={i}>{f}</li>)}
                                                           </ul>
                                                           <ul className="text-xs text-blue-200/70 list-disc list-inside space-y-1">
                                                               {msg.neutral_analysis.interpretations.map((f, i) => <li key={i}>{f}</li>)}
                                                           </ul>
                                                        </div>
                                                    </div>
                                                )}
                                                
                                                {msg.arguments && (
                                                    <div className="grid md:grid-cols-2 gap-3">
                                                        <div className="bg-emerald-900/10 border border-emerald-800/20 rounded-lg p-3">
                                                            <h4 className="text-emerald-400 font-medium mb-2 text-xs uppercase">Arguments For</h4>
                                                            <ul className="text-xs text-emerald-200/70 list-disc list-inside space-y-1">
                                                                {msg.arguments.for.map((f, i) => <li key={i}>{f}</li>)}
                                                            </ul>
                                                        </div>
                                                        <div className="bg-red-900/10 border border-red-800/20 rounded-lg p-3">
                                                            <h4 className="text-red-400 font-medium mb-2 text-xs uppercase">Arguments Against</h4>
                                                            <ul className="text-xs text-red-200/70 list-disc list-inside space-y-1">
                                                                {msg.arguments.against.map((f, i) => <li key={i}>{f}</li>)}
                                                            </ul>
                                                        </div>
                                                    </div>
                                                )}
                                             </div>
                                          )}
                                          
                                          {msg.citations && msg.citations.length > 0 && (
                                              <div className="mt-4 not-prose bg-[#18181b] border border-[#27272a] rounded-xl overflow-hidden">
                                                  <div className="px-4 py-2 bg-[#1f1f23] border-b border-[#27272a] flex items-center justify-between">
                                                      <h4 className="text-[10px] font-semibold text-gray-400 uppercase tracking-wider flex items-center gap-2">
                                                          <BookOpen className="w-3 h-3" /> Verifiable Sources
                                                      </h4>
                                                  </div>
                                                  <div className="p-1">
                                                      {msg.citations.map((cite, i) => {
                                                          const rawSec = cite.section ? String(cite.section) : "";
                                                          const isNullSec = !rawSec || rawSec.toLowerCase().includes("null") || rawSec.toLowerCase() === "undefined";
                                                          const cleanSec = isNullSec ? (cite.source || "Statutory Reference") : rawSec.replace(/Section\s+Section/gi, "Section");
                                                          const linkUrl = getKanoonLink(cite.source, cite.section, cite.url);
                                                          
                                                          return (
                                                              <a 
                                                                  key={i} 
                                                                  href={linkUrl}
                                                                  target="_blank"
                                                                  rel="noopener noreferrer"
                                                                  className="flex items-center justify-between px-3 py-2 hover:bg-[#27272a] rounded-lg group transition-colors text-xs"
                                                              >
                                                                  <div className="flex flex-col min-w-0">
                                                                      <span className="font-medium text-purple-400 group-hover:text-purple-300 transition-colors truncate">
                                                                           {cleanSec}
                                                                      </span>
                                                                      <span className="text-[10px] text-gray-500 truncate">{cite.source || "Indian Statute"}</span>
                                                                  </div>
                                                                  <div className="opacity-0 group-hover:opacity-100 transition-opacity shrink-0 ml-2">
                                                                      <ExternalLink className="w-3 h-3 text-gray-400 hover:text-white" />
                                                                  </div>
                                                              </a>
                                                          );
                                                      })}
                                                  </div>
                                              </div>
                                          )}
                                           
                                           <div className="mt-4 flex gap-2 justify-start opacity-70 hover:opacity-100 transition-opacity">
                                              <Button variant="ghost" size="sm" className="h-6 text-[10px] text-gray-500 hover:text-gray-300 px-2" onClick={() => exportPDF(msg, "Legal Research Analysis")}>
                                                  <Download className="h-3 w-3 mr-1.5" /> Save PDF
                                              </Button>
                                          </div>
                                      </div>
                                  ) : (
                                      <p>{msg.content}</p>
                                  )}
                              </div>
                          </motion.div>
                      ))}
                      
                      {isLoading && (
                          <motion.div 
                              initial={{ opacity: 0 }} 
                              animate={{ opacity: 1 }}
                              className="flex items-center gap-4 pl-0"
                          >
                               <div className="w-8 h-8 rounded-full bg-purple-600/20 flex items-center justify-center shrink-0 border border-purple-500/20">
                                  <Loader2 className="h-4 w-4 animate-spin text-purple-400" />
                               </div>
                              <span className="text-xs font-mono text-gray-500 animate-pulse">{loadingText}</span>
                          </motion.div>
                      )}
                  </AnimatePresence>
                  <div ref={scrollRef} />
              </div>
           </div>

           {/* Input Area */}
           <div className="w-full max-w-3xl mx-auto px-4 pb-6 pt-2">
               <div className="relative flex items-center gap-2 bg-[#18181b] border border-[#27272a] rounded-xl p-2 shadow-lg focus-within:ring-1 focus-within:ring-purple-500/30 transition-all">
                   <Button 
                       variant={isListening ? "destructive" : "ghost"} 
                       size="icon" 
                       onClick={startListening}
                       className={cn("rounded-lg h-9 w-9 shrink-0", isListening ? "" : "text-gray-400 hover:text-white hover:bg-[#27272a]")}
                   >
                       {isListening ? <MicOff className="h-4 w-4" /> : <Mic className="h-4 w-4" />}
                   </Button>
                   
                   <Input 
                       value={input}
                       onChange={(e) => setInput(e.target.value)}
                       onKeyDown={(e) => e.key === 'Enter' && handleSend()}
                       placeholder={isListening ? "Listening..." : "Ask your legal question..."}
                       className="border-0 bg-transparent focus-visible:ring-0 text-white placeholder:text-gray-500 h-9 px-2 shadow-none"
                   />
                   
                   <Button 
                       size="icon" 
                       onClick={() => handleSend()}
                       disabled={!input.trim()}
                       className={cn(
                           "rounded-lg h-9 w-9 shrink-0 transition-all",
                           input.trim() ? "bg-purple-600 hover:bg-purple-500 text-white" : "bg-[#27272a] text-gray-500 cursor-not-allowed"
                       )}
                   >
                       <Send className="h-4 w-4" />
                   </Button>
               </div>
               <div className="mt-2 text-[10px] text-center text-gray-600">
                   AI can make mistakes. Please verify important information.
               </div>
           </div>

        </main>
      </div>

    </div>
  );
};

export default ChatPage;
