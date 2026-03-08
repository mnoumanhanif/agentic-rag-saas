import type { Reflection, Source } from "@/lib/api";

export interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  sources?: Source[];
  steps?: string[];
  reflection?: Reflection | null;
  queryAnalysis?: Record<string, unknown> | null;
  timestamp: Date;
  isLoading?: boolean;
  reaction?: "thumbsUp" | "thumbsDown" | null;
}

export interface Conversation {
  id: string;
  title: string;
  messages: Message[];
  createdAt: Date;
  updatedAt: Date;
  isPinned?: boolean;
}
