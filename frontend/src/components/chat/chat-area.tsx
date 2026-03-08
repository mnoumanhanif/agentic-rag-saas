"use client";

import React, { useRef, useEffect } from "react";
import { motion } from "framer-motion";
import { MessageSquarePlus, Sparkles } from "lucide-react";
import { useChatStore } from "@/hooks/use-chat-store";
import { useChat } from "@/hooks/use-chat";
import { ChatMessage } from "@/components/chat/chat-message";
import { ChatInput } from "@/components/chat/chat-input";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";

export function ChatArea() {
  const { getActiveConversation, createConversation, activeConversationId } =
    useChatStore();
  const { sendMessage, retryMessage, isLoading } = useChat();
  const scrollRef = useRef<HTMLDivElement>(null);
  const conversation = getActiveConversation();
  const messages = conversation?.messages ?? [];

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  if (!activeConversationId) {
    return (
      <div className="flex flex-1 flex-col">
        <EmptyState
          onNewChat={createConversation}
          onSend={sendMessage}
          isLoading={isLoading}
        />
      </div>
    );
  }

  if (messages.length === 0) {
    return (
      <div className="flex flex-1 flex-col">
        <EmptyState
          onNewChat={() => {}}
          onSend={sendMessage}
          isLoading={isLoading}
        />
      </div>
    );
  }

  return (
    <div className="flex flex-1 flex-col min-h-0">
      {/* Messages */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto scroll-smooth">
        <div className="mx-auto max-w-3xl divide-y divide-border/50">
          {messages.map((message) => (
            <ChatMessage
              key={message.id}
              message={message}
              onRetry={
                message.role === "assistant" && !message.isLoading
                  ? retryMessage
                  : undefined
              }
            />
          ))}
        </div>
      </div>

      {/* Input */}
      <ChatInput onSend={sendMessage} isLoading={isLoading} />
    </div>
  );
}

function EmptyState({
  onNewChat,
  onSend,
  isLoading,
}: {
  onNewChat: () => void;
  onSend: (msg: string) => void;
  isLoading: boolean;
}) {
  const suggestions = [
    "What are the key points in this document?",
    "Summarize the main findings",
    "What conclusions were drawn?",
    "Compare the different approaches mentioned",
  ];

  return (
    <div className="flex flex-1 flex-col items-center justify-center p-6">
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.4 }}
        className="text-center space-y-6 max-w-lg"
      >
        <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-br from-violet-500 to-indigo-600 shadow-lg">
          <Sparkles className="h-8 w-8 text-white" />
        </div>
        <div>
          <h2 className="text-2xl font-bold text-foreground">
            Agentic RAG System
          </h2>
          <p className="mt-2 text-muted-foreground">
            Upload PDFs and ask questions. The system uses intelligent retrieval,
            reasoning, and self-reflection to provide accurate answers.
          </p>
        </div>

        <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
          {suggestions.map((suggestion) => (
            <button
              key={suggestion}
              onClick={() => onSend(suggestion)}
              disabled={isLoading}
              className="rounded-xl border bg-card p-3 text-left text-sm text-muted-foreground hover:bg-accent hover:text-accent-foreground transition-colors"
            >
              {suggestion}
            </button>
          ))}
        </div>
      </motion.div>

      <div className="mt-8 w-full max-w-3xl">
        <ChatInput onSend={onSend} isLoading={isLoading} />
      </div>
    </div>
  );
}
