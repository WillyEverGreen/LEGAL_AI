import { motion } from 'framer-motion';
import { Scale, Bot, FileText, ShieldCheck, BookOpen, Lock, ArrowUpRight } from 'lucide-react';
import { Link } from 'react-router-dom';

const FeaturesGridBento = () => {
  const features = [
    {
      title: 'IPC vs BNS Comparison',
      description: 'Side-by-side analysis of Indian Penal Code and Bharatiya Nyaya Sanhita with instant diff highlighting and penalty shifts.',
      icon: Scale,
      iconColor: 'text-purple-400',
      iconBg: 'bg-purple-500/10 border-purple-500/20',
      desktopSpan: 'md:col-span-2 md:row-span-1',
      link: '/compare',
      actionLabel: 'Compare sections'
    },
    {
      title: 'AI Legal Assistant',
      description: 'Ask complex legal questions in natural language and receive grounded answers with Supreme Court citations and statutory cross-references.',
      icon: Bot,
      iconColor: 'text-blue-400',
      iconBg: 'bg-blue-500/10 border-blue-500/20',
      desktopSpan: 'md:col-span-1 md:row-span-2',
      link: '/chat',
      actionLabel: 'Start research'
    },
    {
      title: 'Document Summarizer',
      description: 'Condense lengthy petitions, contracts, and judgments into actionable legal insights in seconds.',
      icon: FileText,
      iconColor: 'text-emerald-400',
      iconBg: 'bg-emerald-500/10 border-emerald-500/20',
      desktopSpan: 'md:col-span-1 md:row-span-1',
      link: '/summarize',
      actionLabel: 'Upload document'
    },
    {
      title: 'Neutral Analysis',
      description: 'Unbiased AI evaluation of legal ambiguities, prospective defense positions, and prosecution strengths.',
      icon: ShieldCheck,
      iconColor: 'text-amber-400',
      iconBg: 'bg-amber-500/10 border-amber-500/20',
      desktopSpan: 'md:col-span-1 md:row-span-1',
      link: '/chat',
      actionLabel: 'Analyze case'
    },
    {
      title: 'Case Law Search',
      description: 'Search through landmark Supreme Court precedents, ratio decidendi, and verified constitutional judgments.',
      icon: BookOpen,
      iconColor: 'text-indigo-400',
      iconBg: 'bg-indigo-500/10 border-indigo-500/20',
      desktopSpan: 'md:col-span-1 md:row-span-1',
      link: '/chat',
      actionLabel: 'Find precedents'
    },
    {
      title: 'Enterprise-Grade Security',
      description: 'Strict confidentiality protocols and privacy safeguards ensuring all sensitive legal inquiries remain protected.',
      icon: Lock,
      iconColor: 'text-rose-400',
      iconBg: 'bg-rose-500/10 border-rose-500/20',
      desktopSpan: 'md:col-span-2 md:row-span-1',
      link: '/draft',
      actionLabel: 'Draft securely'
    }
  ];

  const containerVariants = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: {
        staggerChildren: 0.08
      }
    }
  };

  const itemVariants = {
    hidden: { opacity: 0, y: 16 },
    visible: {
      opacity: 1,
      y: 0,
      transition: {
        duration: 0.4
      }
    }
  };

  return (
    <section id="features" className="py-16 md:py-24 px-4 sm:px-6">
      <div className="max-w-5xl mx-auto">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5 }}
          className="text-center mb-12 md:mb-16"
        >
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-purple-500/10 border border-purple-500/20 text-purple-300 text-xs font-medium uppercase tracking-wider mb-4">
            Capabilities
          </div>
          <h2 className="text-3xl sm:text-4xl md:text-5xl font-bold tracking-tight text-white mb-4">
            Powerful Features for Modern Law
          </h2>
          <p className="text-base sm:text-lg text-gray-400 max-w-2xl mx-auto">
            Everything you need to navigate statutory transitions, evaluate cases, and verify citations with confidence.
          </p>
        </motion.div>

        {/* Responsive Grid: single column on mobile, 3 cols with custom spans on desktop */}
        <motion.div
          variants={containerVariants}
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true }}
          className="grid grid-cols-1 md:grid-cols-3 md:grid-rows-3 gap-4 h-auto md:h-[620px]"
        >
          {features.map((feature, index) => {
            const Icon = feature.icon;
            return (
              <motion.div
                key={index}
                variants={itemVariants}
                whileHover={{ y: -3 }}
                transition={{ duration: 0.2 }}
                className={`
                  ${feature.desktopSpan}
                  group relative rounded-2xl p-6 sm:p-7
                  bg-[#0c0c0e] border border-white/10 hover:border-purple-500/30
                  transition-all duration-300 flex flex-col justify-between
                  shadow-lg hover:shadow-purple-500/5
                `}
              >
                <div>
                  <div className="flex items-center justify-between mb-4">
                    <div className={`w-11 h-11 rounded-xl ${feature.iconBg} border flex items-center justify-center transition-transform group-hover:scale-110 duration-200`}>
                      <Icon className={`w-5 h-5 ${feature.iconColor}`} />
                    </div>
                    <Link
                      to={feature.link}
                      className="opacity-0 group-hover:opacity-100 transition-opacity p-1.5 rounded-lg hover:bg-white/10 text-gray-400 hover:text-white"
                      aria-label={feature.title}
                    >
                      <ArrowUpRight className="w-4 h-4" />
                    </Link>
                  </div>

                  <h3 className="text-lg sm:text-xl font-semibold text-white mb-2 tracking-tight">
                    {feature.title}
                  </h3>
                  <p className="text-sm text-gray-400 leading-relaxed">
                    {feature.description}
                  </p>
                </div>

                <div className="pt-4 mt-auto">
                  <Link
                    to={feature.link}
                    className="inline-flex items-center gap-1.5 text-xs font-medium text-gray-400 group-hover:text-purple-300 transition-colors"
                  >
                    <span>{feature.actionLabel}</span>
                    <ArrowUpRight className="w-3.5 h-3.5 opacity-60 group-hover:opacity-100 group-hover:translate-x-0.5 group-hover:-translate-y-0.5 transition-transform" />
                  </Link>
                </div>
              </motion.div>
            );
          })}
        </motion.div>
      </div>
    </section>
  );
};

export default FeaturesGridBento;
