"use client";

import React, { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Copy,
  Check,
  ChevronDown,
  ChevronRight,
  BookOpen,
  Layers,
  Sparkles,
  User,
  Bot,
  RotateCcw,
  ThumbsUp,
  ThumbsDown,
  Brain,
  Search as SearchIcon,
  Zap,
  FileText,
} from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { useChatStore } from "@/hooks/use-chat-store";
import type { Message } from "@/types/chat";

interface ChatMessageProps {
  message: Message;
  onRetry?: (messageId: string) => void;
}

export function ChatMessage({ message, onRetry }: ChatMessageProps) {
  const isUser = message.role === "user";
  const { showReasoning, updateMessage, activeConversationId } = useChatStore();

  const handleReaction = (reaction: "thumbsUp" | "thumbsDown") => {
    if (!activeConversationId) return;
    updateMessage(activeConversationId, message.id, {
      reaction: message.reaction === reaction ? null : reaction,
    });
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className={cn(
        "flex gap-3 px-4 py-4 md:px-6",
        isUser && "bg-transparent"
      )}
    >
      {/* Avatar */}
      <div
        className={cn(
          "flex h-8 w-8 shrink-0 items-center justify-center rounded-full",
          isUser
            ? "bg-primary text-primary-foreground"
            : "bg-gradient-to-br from-violet-500 to-indigo-600 text-white"
        )}
      >
        {isUser ? <User className="h-4 w-4" /> : <Bot className="h-4 w-4" />}
      </div>

      {/* Content */}
      <div className="flex-1 min-w-0 space-y-2">
        <div className="flex items-center gap-2">
          <span className="text-sm font-semibold text-foreground">
            {isUser ? "You" : "Assistant"}
          </span>
          <span className="text-xs text-muted-foreground">
            {message.timestamp.toLocaleTimeString([], {
              hour: "2-digit",
              minute: "2-digit",
            })}
          </span>
        </div>

        {message.isLoading ? (
          <LoadingDots />
        ) : (
          <>
            <MessageContent content={message.content} />

            {/* Action buttons */}
            {!isUser && (
              <div className="flex items-center gap-1 mt-1">
                <CopyButton text={message.content} />
                {onRetry && (
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => onRetry(message.id)}
                    className="h-7 gap-1.5 text-xs text-muted-foreground"
                  >
                    <RotateCcw className="h-3 w-3" />
                    Retry
                  </Button>
                )}
                <div className="flex items-center gap-0.5 ml-2">
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={() => handleReaction("thumbsUp")}
                    className={cn(
                      "h-7 w-7",
                      message.reaction === "thumbsUp" &&
                        "text-green-500 bg-green-500/10"
                    )}
                  >
                    <ThumbsUp className="h-3 w-3" />
                  </Button>
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={() => handleReaction("thumbsDown")}
                    className={cn(
                      "h-7 w-7",
                      message.reaction === "thumbsDown" &&
                        "text-red-500 bg-red-500/10"
                    )}
                  >
                    <ThumbsDown className="h-3 w-3" />
                  </Button>
                </div>
              </div>
            )}

            {/* Source Citations Panel */}
            {message.sources && message.sources.length > 0 && (
              <SourceCards sources={message.sources} />
            )}

            {/* Agent Reasoning - shown when toggle is on */}
            {showReasoning && (
              <>
                {message.steps && message.steps.length > 0 && (
                  <AgentReasoningViewer
                    steps={message.steps}
                    queryAnalysis={message.queryAnalysis}
                  />
                )}
                {message.reflection && (
                  <ReflectionCard reflection={message.reflection} />
                )}
              </>
            )}

            {/* Always show pipeline steps toggle (even without reasoning mode) */}
            {!showReasoning &&
              message.steps &&
              message.steps.length > 0 && (
                <PipelineSteps steps={message.steps} />
              )}
            {!showReasoning && message.reflection && (
              <ReflectionCard reflection={message.reflection} />
            )}
          </>
        )}
      </div>
    </motion.div>
  );
}

function LoadingDots() {
  return (
    <div className="flex items-center gap-1.5 py-2">
      {[0, 1, 2].map((i) => (
        <motion.div
          key={i}
          className="h-2 w-2 rounded-full bg-muted-foreground/40"
          animate={{ opacity: [0.3, 1, 0.3], scale: [0.85, 1, 0.85] }}
          transition={{
            duration: 1.2,
            repeat: Infinity,
            delay: i * 0.2,
          }}
        />
      ))}
    </div>
  );
}

function MessageContent({ content }: { content: string }) {
  return (
    <div className="prose prose-sm dark:prose-invert max-w-none break-words">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          code({ className, children, ...props }) {
            const isInline = !className;
            if (isInline) {
              return (
                <code
                  className="rounded bg-muted px-1.5 py-0.5 text-sm font-mono"
                  {...props}
                >
                  {children}
                </code>
              );
            }
            const language = className?.replace("language-", "") || "";
            return (
              <div className="relative group my-3">
                {language && (
                  <div
                    className="absolute top-0 left-0 px-3 py-1 text-[10px] font-mono text-zinc-400 uppercase"
                    aria-label={`Code language: ${language}`}
                  >
                    {language}
                  </div>
                )}
                <pre className="overflow-x-auto rounded-lg bg-zinc-900 dark:bg-zinc-950 p-4 pt-7 text-sm">
                  <code
                    className={cn("font-mono text-zinc-100", className)}
                    {...props}
                  >
                    {children}
                  </code>
                </pre>
                <CopyButton
                  text={String(children)}
                  className="absolute top-1.5 right-2 opacity-0 group-hover:opacity-100"
                />
              </div>
            );
          },
          p({ children }) {
            return (
              <p className="mb-3 last:mb-0 leading-relaxed">{children}</p>
            );
          },
          ul({ children }) {
            return (
              <ul className="mb-3 list-disc pl-5 space-y-1">{children}</ul>
            );
          },
          ol({ children }) {
            return (
              <ol className="mb-3 list-decimal pl-5 space-y-1">{children}</ol>
            );
          },
          a({ href, children }) {
            return (
              <a
                href={href}
                target="_blank"
                rel="noopener noreferrer"
                className="text-primary hover:underline"
              >
                {children}
              </a>
            );
          },
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}

function CopyButton({
  text,
  className,
}: {
  text: string;
  className?: string;
}) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    await navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <Button
      variant="ghost"
      size="sm"
      onClick={handleCopy}
      className={cn("h-7 gap-1.5 text-xs text-muted-foreground", className)}
    >
      {copied ? (
        <Check className="h-3 w-3 text-green-500" />
      ) : (
        <Copy className="h-3 w-3" />
      )}
      {copied ? "Copied" : "Copy"}
    </Button>
  );
}

function SourceCards({
  sources,
}: {
  sources: { content: string; metadata: Record<string, unknown> }[];
}) {
  const [isOpen, setIsOpen] = useState(false);
  const [expandedSource, setExpandedSource] = useState<number | null>(null);

  return (
    <div className="mt-3">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors"
      >
        <BookOpen className="h-4 w-4" />
        <span className="font-medium">
          {sources.length} source{sources.length !== 1 ? "s" : ""}
        </span>
        <Badge variant="secondary" className="text-[10px] px-1.5 py-0">
          Retrieved
        </Badge>
        {isOpen ? (
          <ChevronDown className="h-3 w-3" />
        ) : (
          <ChevronRight className="h-3 w-3" />
        )}
      </button>

      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden"
          >
            <div className="mt-2 grid gap-2">
              {sources.map((source, i) => {
                const isExpanded = expandedSource === i;
                const filename = String(
                  source.metadata?.source ?? "Document"
                );
                const page = source.metadata?.page;
                return (
                  <div
                    key={i}
                    className="rounded-lg border bg-card p-3 text-sm space-y-1 cursor-pointer hover:border-primary/50 transition-colors"
                    onClick={() =>
                      setExpandedSource(isExpanded ? null : i)
                    }
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <FileText className="h-3.5 w-3.5 text-muted-foreground" />
                        <span className="font-medium text-foreground text-xs">
                          {filename}
                        </span>
                        {page !== undefined && (
                          <Badge
                            variant="outline"
                            className="text-[10px] px-1 py-0"
                          >
                            p.{String(page)}
                          </Badge>
                        )}
                      </div>
                      <span className="text-[10px] text-muted-foreground">
                        Source {i + 1}
                      </span>
                    </div>
                    <p
                      className={cn(
                        "text-muted-foreground text-xs",
                        isExpanded ? "" : "line-clamp-3"
                      )}
                    >
                      {source.content}
                    </p>
                    {!isExpanded && source.content.length > 200 && (
                      <span className="text-xs text-primary">
                        Click to expand
                      </span>
                    )}
                  </div>
                );
              })}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

function AgentReasoningViewer({
  steps,
  queryAnalysis,
}: {
  steps: string[];
  queryAnalysis?: Record<string, unknown> | null;
}) {
  const [isOpen, setIsOpen] = useState(true);

  const categorizeStep = (
    step: string
  ): { icon: React.ReactNode; color: string } => {
    const lower = step.toLowerCase();
    if (lower.includes("retriev") || lower.includes("search") || lower.includes("vector")) {
      return {
        icon: <SearchIcon className="h-3 w-3" />,
        color: "text-blue-500",
      };
    }
    if (lower.includes("rerank") || lower.includes("rank")) {
      return {
        icon: <Layers className="h-3 w-3" />,
        color: "text-orange-500",
      };
    }
    if (lower.includes("reason") || lower.includes("think") || lower.includes("analyz")) {
      return {
        icon: <Brain className="h-3 w-3" />,
        color: "text-purple-500",
      };
    }
    if (lower.includes("tool") || lower.includes("action") || lower.includes("execut")) {
      return { icon: <Zap className="h-3 w-3" />, color: "text-yellow-500" };
    }
    return {
      icon: <Sparkles className="h-3 w-3" />,
      color: "text-muted-foreground",
    };
  };

  return (
    <div className="mt-3 rounded-lg border border-violet-500/20 bg-violet-500/5 p-3">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2 text-sm font-medium text-violet-600 dark:text-violet-400"
      >
        <Brain className="h-4 w-4" />
        <span>Agent Reasoning</span>
        <Badge
          variant="secondary"
          className="text-[10px] px-1.5 py-0 bg-violet-500/10 text-violet-600 dark:text-violet-400"
        >
          {steps.length} steps
        </Badge>
        {isOpen ? (
          <ChevronDown className="h-3 w-3" />
        ) : (
          <ChevronRight className="h-3 w-3" />
        )}
      </button>

      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden"
          >
            {/* Query Analysis */}
            {queryAnalysis && Object.keys(queryAnalysis).length > 0 && (
              <div className="mt-2 rounded-md bg-background/50 p-2 text-xs">
                <span className="font-medium text-foreground">
                  Query Analysis:
                </span>
                <div className="mt-1 space-y-0.5 text-muted-foreground">
                  {Object.entries(queryAnalysis).map(([key, value]) => (
                    <div key={key} className="flex items-start gap-1">
                      <span className="font-mono text-[10px] text-primary">
                        {key}:
                      </span>
                      <span>{String(value)}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Pipeline Steps */}
            <div className="mt-2 space-y-1">
              {steps.map((step, i) => {
                const { icon, color } = categorizeStep(step);
                return (
                  <motion.div
                    key={i}
                    initial={{ opacity: 0, x: -10 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: i * 0.05 }}
                    className="flex items-start gap-2 text-xs"
                  >
                    <div
                      className={cn(
                        "mt-0.5 flex h-4 w-4 items-center justify-center rounded-full bg-background",
                        color
                      )}
                    >
                      {icon}
                    </div>
                    <span className="text-muted-foreground flex-1">
                      {step}
                    </span>
                    <span className="text-[10px] text-muted-foreground/50 font-mono">
                      #{i + 1}
                    </span>
                  </motion.div>
                );
              })}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

function PipelineSteps({ steps }: { steps: string[] }) {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <div className="mt-2">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors"
      >
        <Layers className="h-4 w-4" />
        <span className="font-medium">Pipeline steps</span>
        {isOpen ? (
          <ChevronDown className="h-3 w-3" />
        ) : (
          <ChevronRight className="h-3 w-3" />
        )}
      </button>

      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden"
          >
            <div className="mt-2 space-y-1 pl-2 border-l-2 border-border">
              {steps.map((step, i) => (
                <div
                  key={i}
                  className="text-xs text-muted-foreground pl-3 py-0.5"
                >
                  {step}
                </div>
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

function ReflectionCard({
  reflection,
}: {
  reflection: { score: number; feedback?: string; is_faithful?: boolean };
}) {
  const [isOpen, setIsOpen] = useState(false);
  const scoreColor =
    reflection.score >= 0.8
      ? "text-green-500"
      : reflection.score >= 0.5
        ? "text-yellow-500"
        : "text-red-500";

  const scorePercent = (reflection.score * 100).toFixed(0);

  return (
    <div className="mt-2">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors"
      >
        <Sparkles className="h-4 w-4" />
        <span className="font-medium">Reflection</span>
        <span className={cn("font-mono text-xs", scoreColor)}>
          {scorePercent}%
        </span>
        {isOpen ? (
          <ChevronDown className="h-3 w-3" />
        ) : (
          <ChevronRight className="h-3 w-3" />
        )}
      </button>

      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden"
          >
            <div className="mt-2 rounded-lg border bg-card p-3 text-sm space-y-2">
              <div className="flex items-center gap-4">
                <div className="flex items-center gap-2">
                  <div className="h-8 w-8 rounded-full border-2 flex items-center justify-center">
                    <span className={cn("font-mono text-xs font-bold", scoreColor)}>
                      {scorePercent}
                    </span>
                  </div>
                  <span className="text-xs text-muted-foreground">
                    Quality Score
                  </span>
                </div>
                {reflection.is_faithful !== undefined && (
                  <Badge
                    variant={reflection.is_faithful ? "secondary" : "destructive"}
                    className="text-[10px]"
                  >
                    {reflection.is_faithful
                      ? "✓ Faithful"
                      : "⚠ May be unfaithful"}
                  </Badge>
                )}
              </div>
              {/* Score bar */}
              <div className="w-full h-1.5 bg-muted rounded-full overflow-hidden">
                <motion.div
                  className={cn(
                    "h-full rounded-full",
                    reflection.score >= 0.8
                      ? "bg-green-500"
                      : reflection.score >= 0.5
                        ? "bg-yellow-500"
                        : "bg-red-500"
                  )}
                  initial={{ width: 0 }}
                  animate={{ width: `${reflection.score * 100}%` }}
                  transition={{ duration: 0.5, delay: 0.1 }}
                />
              </div>
              {reflection.feedback && (
                <p className="text-xs text-muted-foreground">
                  {reflection.feedback}
                </p>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
