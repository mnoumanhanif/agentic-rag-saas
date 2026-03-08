"use client";

import { useState, useCallback } from "react";
import { queryRAG, type QueryResponse } from "@/lib/api";
import { useChatStore } from "@/hooks/use-chat-store";
import type { Message } from "@/types/chat";

function generateId() {
  return Math.random().toString(36).substring(2, 15);
}

export function useChat() {
  const [isLoading, setIsLoading] = useState(false);

  const {
    activeConversationId,
    createConversation,
    addMessage,
    updateMessage,
    getActiveConversation,
  } = useChatStore();

  const sendMessage = useCallback(
    async (content: string) => {
      if (!content.trim() || isLoading) return;

      let convId = activeConversationId;
      if (!convId) {
        convId = createConversation();
      }

      const userMessage: Message = {
        id: generateId(),
        role: "user",
        content: content.trim(),
        timestamp: new Date(),
      };
      addMessage(convId, userMessage);

      const assistantId = generateId();
      const loadingMessage: Message = {
        id: assistantId,
        role: "assistant",
        content: "",
        timestamp: new Date(),
        isLoading: true,
      };
      addMessage(convId, loadingMessage);

      setIsLoading(true);

      try {
        const conversation = getActiveConversation();
        const chatHistory = (conversation?.messages ?? [])
          .filter((m) => !m.isLoading && m.id !== userMessage.id)
          .map((m) => ({ role: m.role, content: m.content }));

        const response: QueryResponse = await queryRAG({
          query: content.trim(),
          chat_history: chatHistory,
        });

        updateMessage(convId, assistantId, {
          content: response.answer,
          sources: response.sources,
          steps: response.steps,
          reflection: response.reflection,
          queryAnalysis: response.query_analysis,
          isLoading: false,
        });
      } catch (error) {
        const errorMsg =
          error instanceof Error
            ? error.message
            : "An unexpected error occurred";
        updateMessage(convId, assistantId, {
          content: `⚠️ ${errorMsg}`,
          isLoading: false,
        });
      } finally {
        setIsLoading(false);
      }
    },
    [
      activeConversationId,
      createConversation,
      addMessage,
      updateMessage,
      getActiveConversation,
      isLoading,
    ]
  );

  const retryMessage = useCallback(
    async (messageId: string) => {
      if (isLoading) return;

      const conversation = getActiveConversation();
      if (!conversation) return;

      // Find the assistant message to retry and the preceding user message
      const msgIndex = conversation.messages.findIndex(
        (m) => m.id === messageId
      );
      if (msgIndex < 0) return;

      const assistantMsg = conversation.messages[msgIndex];
      if (assistantMsg.role !== "assistant") return;

      // Find the user message before this assistant response
      let userContent = "";
      for (let i = msgIndex - 1; i >= 0; i--) {
        if (conversation.messages[i].role === "user") {
          userContent = conversation.messages[i].content;
          break;
        }
      }
      if (!userContent) return;

      // Reset assistant message to loading
      updateMessage(conversation.id, messageId, {
        content: "",
        sources: undefined,
        steps: undefined,
        reflection: undefined,
        queryAnalysis: undefined,
        isLoading: true,
      });

      setIsLoading(true);

      try {
        const chatHistory = conversation.messages
          .slice(0, msgIndex - 1)
          .filter((m) => !m.isLoading)
          .map((m) => ({ role: m.role, content: m.content }));

        const response: QueryResponse = await queryRAG({
          query: userContent,
          chat_history: chatHistory,
        });

        updateMessage(conversation.id, messageId, {
          content: response.answer,
          sources: response.sources,
          steps: response.steps,
          reflection: response.reflection,
          queryAnalysis: response.query_analysis,
          isLoading: false,
        });
      } catch (error) {
        const errorMsg =
          error instanceof Error
            ? error.message
            : "An unexpected error occurred";
        updateMessage(conversation.id, messageId, {
          content: `⚠️ ${errorMsg}`,
          isLoading: false,
        });
      } finally {
        setIsLoading(false);
      }
    },
    [getActiveConversation, updateMessage, isLoading]
  );

  return { sendMessage, retryMessage, isLoading };
}
