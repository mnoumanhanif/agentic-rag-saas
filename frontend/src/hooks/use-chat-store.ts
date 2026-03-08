import { create } from "zustand";
import type { Conversation, Message } from "@/types/chat";

function generateId() {
  return Math.random().toString(36).substring(2, 15);
}

type ActiveView = "chat" | "dashboard" | "documents" | "admin";

interface ChatStore {
  conversations: Conversation[];
  activeConversationId: string | null;
  sidebarOpen: boolean;
  darkMode: boolean;
  searchQuery: string;
  showReasoning: boolean;
  activeView: ActiveView;

  // Actions
  createConversation: () => string;
  setActiveConversation: (id: string) => void;
  addMessage: (conversationId: string, message: Message) => void;
  updateMessage: (
    conversationId: string,
    messageId: string,
    updates: Partial<Message>
  ) => void;
  deleteConversation: (id: string) => void;
  renameConversation: (id: string, title: string) => void;
  togglePinConversation: (id: string) => void;
  toggleSidebar: () => void;
  toggleDarkMode: () => void;
  toggleReasoning: () => void;
  setSearchQuery: (query: string) => void;
  setActiveView: (view: ActiveView) => void;
  getActiveConversation: () => Conversation | undefined;
  getFilteredConversations: () => {
    pinned: Conversation[];
    recent: Conversation[];
  };
}

export const useChatStore = create<ChatStore>((set, get) => ({
  conversations: [],
  activeConversationId: null,
  sidebarOpen: true,
  darkMode: true,
  searchQuery: "",
  showReasoning: false,
  activeView: "chat",

  createConversation: () => {
    const id = generateId();
    const conversation: Conversation = {
      id,
      title: "New Chat",
      messages: [],
      createdAt: new Date(),
      updatedAt: new Date(),
      isPinned: false,
    };
    set((state) => ({
      conversations: [conversation, ...state.conversations],
      activeConversationId: id,
      activeView: "chat",
    }));
    return id;
  },

  setActiveConversation: (id) =>
    set({ activeConversationId: id, activeView: "chat" }),

  addMessage: (conversationId, message) =>
    set((state) => ({
      conversations: state.conversations.map((conv) => {
        if (conv.id !== conversationId) return conv;
        const updated = {
          ...conv,
          messages: [...conv.messages, message],
          updatedAt: new Date(),
        };
        // Update title from first user message
        if (message.role === "user" && conv.messages.length === 0) {
          updated.title =
            message.content.length > 40
              ? message.content.slice(0, 40) + "…"
              : message.content;
        }
        return updated;
      }),
    })),

  updateMessage: (conversationId, messageId, updates) =>
    set((state) => ({
      conversations: state.conversations.map((conv) =>
        conv.id !== conversationId
          ? conv
          : {
              ...conv,
              messages: conv.messages.map((msg) =>
                msg.id !== messageId ? msg : { ...msg, ...updates }
              ),
              updatedAt: new Date(),
            }
      ),
    })),

  deleteConversation: (id) =>
    set((state) => {
      const filtered = state.conversations.filter((c) => c.id !== id);
      return {
        conversations: filtered,
        activeConversationId:
          state.activeConversationId === id
            ? filtered[0]?.id ?? null
            : state.activeConversationId,
      };
    }),

  renameConversation: (id, title) =>
    set((state) => ({
      conversations: state.conversations.map((conv) =>
        conv.id !== id ? conv : { ...conv, title, updatedAt: new Date() }
      ),
    })),

  togglePinConversation: (id) =>
    set((state) => ({
      conversations: state.conversations.map((conv) =>
        conv.id !== id
          ? conv
          : { ...conv, isPinned: !conv.isPinned, updatedAt: new Date() }
      ),
    })),

  toggleSidebar: () => set((state) => ({ sidebarOpen: !state.sidebarOpen })),
  toggleDarkMode: () => set((state) => ({ darkMode: !state.darkMode })),
  toggleReasoning: () =>
    set((state) => ({ showReasoning: !state.showReasoning })),
  setSearchQuery: (query) => set({ searchQuery: query }),
  setActiveView: (view) => set({ activeView: view }),

  getActiveConversation: () => {
    const state = get();
    return state.conversations.find(
      (c) => c.id === state.activeConversationId
    );
  },

  getFilteredConversations: () => {
    const state = get();
    const query = state.searchQuery.toLowerCase();
    const filtered = query
      ? state.conversations.filter(
          (c) =>
            c.title.toLowerCase().includes(query) ||
            c.messages.some((m) => m.content.toLowerCase().includes(query))
        )
      : state.conversations;
    return {
      pinned: filtered.filter((c) => c.isPinned),
      recent: filtered.filter((c) => !c.isPinned),
    };
  },
}));
