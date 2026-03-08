"use client";

import React, { useState, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  MessageSquarePlus,
  Trash2,
  MessageSquare,
  ChevronLeft,
  Upload,
  FileText,
  CheckCircle2,
  AlertCircle,
  Loader2,
  X,
  Search,
  Pin,
  PinOff,
  Pencil,
  Check,
  LayoutDashboard,
  FolderOpen,
  ShieldCheck,
  LogOut,
} from "lucide-react";
import { useChatStore } from "@/hooks/use-chat-store";
import { useAuthStore } from "@/hooks/use-auth-store";
import { uploadFiles } from "@/lib/api";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";

export function Sidebar() {
  const {
    activeConversationId,
    sidebarOpen,
    searchQuery,
    activeView,
    createConversation,
    setActiveConversation,
    deleteConversation,
    renameConversation,
    togglePinConversation,
    toggleSidebar,
    setSearchQuery,
    setActiveView,
    getFilteredConversations,
  } = useChatStore();

  const user = useAuthStore((s) => s.user);
  const logout = useAuthStore((s) => s.logout);

  const { pinned, recent } = getFilteredConversations();

  return (
    <>
      {/* Mobile overlay */}
      <AnimatePresence>
        {sidebarOpen && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 0.5 }}
            exit={{ opacity: 0 }}
            onClick={toggleSidebar}
            className="fixed inset-0 z-20 bg-black md:hidden"
          />
        )}
      </AnimatePresence>

      {/* Sidebar */}
      <motion.aside
        initial={false}
        animate={{ width: sidebarOpen ? 280 : 0 }}
        transition={{ duration: 0.2, ease: "easeInOut" }}
        className={cn(
          "fixed md:relative z-30 flex h-full flex-col overflow-hidden border-r bg-sidebar",
          "md:z-0"
        )}
      >
        <div className="flex h-full w-[280px] flex-col">
          {/* Header */}
          <div className="flex items-center justify-between p-4 border-b">
            <h1 className="text-lg font-bold bg-gradient-to-r from-violet-600 to-indigo-600 bg-clip-text text-transparent">
              RAG Chat
            </h1>
            <Button
              variant="ghost"
              size="icon"
              onClick={toggleSidebar}
              className="h-8 w-8"
            >
              <ChevronLeft className="h-4 w-4" />
            </Button>
          </div>

          {/* New Chat Button */}
          <div className="p-3">
            <Button
              onClick={() => createConversation()}
              className="w-full justify-start gap-2 bg-gradient-to-r from-violet-600 to-indigo-600 text-white hover:from-violet-700 hover:to-indigo-700 shadow-md"
            >
              <MessageSquarePlus className="h-4 w-4" />
              New Chat
            </Button>
          </div>

          {/* Search */}
          <div className="px-3 pb-2">
            <div className="relative">
              <Search className="absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground" />
              <Input
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search conversations…"
                className="h-8 pl-8 text-xs bg-muted/50"
              />
              {searchQuery && (
                <button
                  onClick={() => setSearchQuery("")}
                  className="absolute right-2 top-1/2 -translate-y-1/2"
                >
                  <X className="h-3 w-3 text-muted-foreground" />
                </button>
              )}
            </div>
          </div>

          {/* File Upload */}
          <div className="px-3 pb-3">
            <FileUploadSection />
          </div>

          {/* Navigation */}
          <div className="px-3 pb-3 space-y-1">
            <button
              onClick={() => setActiveView("chat")}
              className={cn(
                "flex w-full items-center gap-2 rounded-lg px-3 py-2 text-sm transition-colors",
                activeView === "chat" ? "bg-accent text-accent-foreground" : "text-muted-foreground hover:bg-accent/50"
              )}
            >
              <MessageSquare className="h-4 w-4" />
              Chat
            </button>
            <button
              onClick={() => setActiveView("documents")}
              className={cn(
                "flex w-full items-center gap-2 rounded-lg px-3 py-2 text-sm transition-colors",
                activeView === "documents" ? "bg-accent text-accent-foreground" : "text-muted-foreground hover:bg-accent/50"
              )}
            >
              <FolderOpen className="h-4 w-4" />
              Documents
            </button>
            <button
              onClick={() => setActiveView("dashboard")}
              className={cn(
                "flex w-full items-center gap-2 rounded-lg px-3 py-2 text-sm transition-colors",
                activeView === "dashboard" ? "bg-accent text-accent-foreground" : "text-muted-foreground hover:bg-accent/50"
              )}
            >
              <LayoutDashboard className="h-4 w-4" />
              Dashboard
            </button>
            {user?.role === "admin" && (
              <button
                onClick={() => setActiveView("admin")}
                className={cn(
                  "flex w-full items-center gap-2 rounded-lg px-3 py-2 text-sm transition-colors",
                  activeView === "admin" ? "bg-accent text-accent-foreground" : "text-muted-foreground hover:bg-accent/50"
                )}
              >
                <ShieldCheck className="h-4 w-4" />
                Admin Panel
              </button>
            )}
          </div>

          {/* Conversations List */}
          <div className="flex-1 overflow-hidden">
            <ScrollArea className="flex-1 px-2">
              <div className="space-y-1 pb-4">
                {/* Pinned Section */}
                {pinned.length > 0 && (
                  <>
                    <div className="px-3 py-2">
                      <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground flex items-center gap-1">
                        <Pin className="h-3 w-3" />
                        Pinned
                      </span>
                    </div>
                    {pinned.map((conv) => (
                      <ConversationItem
                        key={conv.id}
                        id={conv.id}
                        title={conv.title}
                        isActive={conv.id === activeConversationId}
                        isPinned={true}
                        messageCount={conv.messages.length}
                        onSelect={() => setActiveConversation(conv.id)}
                        onDelete={() => deleteConversation(conv.id)}
                        onRename={(title) => renameConversation(conv.id, title)}
                        onTogglePin={() => togglePinConversation(conv.id)}
                      />
                    ))}
                  </>
                )}

                {/* Recent Section */}
                <div className="px-3 py-2">
                  <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                    {pinned.length > 0 ? "Recent" : "History"}
                  </span>
                </div>
                {recent.length === 0 ? (
                  <p className="px-3 py-6 text-center text-sm text-muted-foreground">
                    {searchQuery
                      ? "No matching conversations"
                      : "No conversations yet"}
                  </p>
                ) : (
                  recent.map((conv) => (
                    <ConversationItem
                      key={conv.id}
                      id={conv.id}
                      title={conv.title}
                      isActive={conv.id === activeConversationId}
                      isPinned={false}
                      messageCount={conv.messages.length}
                      onSelect={() => setActiveConversation(conv.id)}
                      onDelete={() => deleteConversation(conv.id)}
                      onRename={(title) => renameConversation(conv.id, title)}
                      onTogglePin={() => togglePinConversation(conv.id)}
                    />
                  ))
                )}
              </div>
            </ScrollArea>
          </div>

          {/* User & Logout */}
          <div className="border-t p-3 space-y-2">
            <div className="flex items-center gap-2 px-2">
              <div className="h-7 w-7 rounded-full bg-gradient-to-br from-violet-500 to-indigo-600 flex items-center justify-center text-xs font-bold text-white">
                {user?.email?.[0]?.toUpperCase() ?? "U"}
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-xs font-medium truncate">{user?.email}</p>
                <p className="text-[10px] text-muted-foreground capitalize">{user?.role}</p>
              </div>
            </div>
            <Button
              variant="ghost"
              size="sm"
              onClick={logout}
              className="w-full justify-start gap-2 text-xs text-muted-foreground hover:text-destructive"
            >
              <LogOut className="h-3.5 w-3.5" />
              Sign Out
            </Button>
          </div>
        </div>
      </motion.aside>
    </>
  );
}

function ConversationItem({
  id,
  title,
  isActive,
  isPinned,
  messageCount,
  onSelect,
  onDelete,
  onRename,
  onTogglePin,
}: {
  id: string;
  title: string;
  isActive: boolean;
  isPinned: boolean;
  messageCount: number;
  onSelect: () => void;
  onDelete: () => void;
  onRename: (title: string) => void;
  onTogglePin: () => void;
}) {
  const [isEditing, setIsEditing] = useState(false);
  const [editTitle, setEditTitle] = useState(title);

  const handleRename = () => {
    if (editTitle.trim()) {
      onRename(editTitle.trim());
    }
    setIsEditing(false);
  };

  return (
    <div
      onClick={() => !isEditing && onSelect()}
      className={cn(
        "group flex items-center gap-2 rounded-lg px-3 py-2.5 text-sm cursor-pointer transition-colors",
        isActive
          ? "bg-accent text-accent-foreground"
          : "text-muted-foreground hover:bg-accent/50 hover:text-foreground"
      )}
    >
      <MessageSquare className="h-4 w-4 shrink-0" />
      {isEditing ? (
        <div className="flex-1 flex items-center gap-1">
          <input
            value={editTitle}
            onChange={(e) => setEditTitle(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") handleRename();
              if (e.key === "Escape") setIsEditing(false);
            }}
            onBlur={handleRename}
            className="flex-1 bg-transparent text-sm outline-none border-b border-primary"
            autoFocus
            onClick={(e) => e.stopPropagation()}
          />
          <button onClick={handleRename}>
            <Check className="h-3.5 w-3.5 text-green-500" />
          </button>
        </div>
      ) : (
        <>
          <span className="flex-1 truncate">{title}</span>
          <span className="text-xs opacity-60">{messageCount}</span>
          <div className="flex items-center gap-0.5 opacity-0 group-hover:opacity-100 transition-opacity">
            <button
              onClick={(e) => {
                e.stopPropagation();
                setEditTitle(title);
                setIsEditing(true);
              }}
              title="Rename"
            >
              <Pencil className="h-3 w-3 text-muted-foreground hover:text-foreground" />
            </button>
            <button
              onClick={(e) => {
                e.stopPropagation();
                onTogglePin();
              }}
              title={isPinned ? "Unpin" : "Pin"}
            >
              {isPinned ? (
                <PinOff className="h-3 w-3 text-muted-foreground hover:text-foreground" />
              ) : (
                <Pin className="h-3 w-3 text-muted-foreground hover:text-foreground" />
              )}
            </button>
            <button
              onClick={(e) => {
                e.stopPropagation();
                onDelete();
              }}
              title="Delete"
            >
              <Trash2 className="h-3 w-3 text-muted-foreground hover:text-destructive" />
            </button>
          </div>
        </>
      )}
    </div>
  );
}

function FileUploadSection() {
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploadResult, setUploadResult] = useState<{
    success: boolean;
    message: string;
  } | null>(null);

  const handleFiles = useCallback(async (files: File[]) => {
    const pdfFiles = files.filter((f) => f.type === "application/pdf");
    if (pdfFiles.length === 0) {
      setUploadResult({
        success: false,
        message: "Only PDF files are supported",
      });
      return;
    }

    setIsUploading(true);
    setUploadResult(null);
    setUploadProgress(0);

    // Simulated progress: increments to 90% during upload, then jumps to 100%
    // on completion. Real progress tracking requires backend streaming support.
    const progressInterval = setInterval(() => {
      setUploadProgress((prev) => Math.min(prev + 10, 90));
    }, 500);

    try {
      const result = await uploadFiles(pdfFiles);
      clearInterval(progressInterval);
      setUploadProgress(100);
      setUploadResult({ success: true, message: result.message });
    } catch (error) {
      clearInterval(progressInterval);
      setUploadResult({
        success: false,
        message: error instanceof Error ? error.message : "Upload failed",
      });
    } finally {
      setIsUploading(false);
      setTimeout(() => setUploadProgress(0), 1000);
    }
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragging(false);
      const files = Array.from(e.dataTransfer.files);
      handleFiles(files);
    },
    [handleFiles]
  );

  const handleInputChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const files = Array.from(e.target.files ?? []);
      handleFiles(files);
      e.target.value = "";
    },
    [handleFiles]
  );

  return (
    <div>
      <div
        onDragOver={(e) => {
          e.preventDefault();
          setIsDragging(true);
        }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={handleDrop}
        className={cn(
          "relative rounded-lg border-2 border-dashed p-4 text-center transition-all duration-200",
          isDragging
            ? "border-primary bg-primary/5 scale-[1.02]"
            : "border-muted-foreground/20 hover:border-muted-foreground/40"
        )}
      >
        <input
          type="file"
          accept=".pdf"
          multiple
          onChange={handleInputChange}
          className="absolute inset-0 cursor-pointer opacity-0"
          disabled={isUploading}
        />
        {isUploading ? (
          <div className="flex flex-col items-center gap-2">
            <Loader2 className="h-6 w-6 animate-spin text-primary" />
            <span className="text-xs text-muted-foreground">
              Processing… {uploadProgress}%
            </span>
            <div className="w-full h-1 bg-muted rounded-full overflow-hidden">
              <motion.div
                className="h-full bg-primary rounded-full"
                initial={{ width: 0 }}
                animate={{ width: `${uploadProgress}%` }}
                transition={{ duration: 0.3 }}
              />
            </div>
          </div>
        ) : (
          <div className="flex flex-col items-center gap-2">
            <Upload className="h-6 w-6 text-muted-foreground" />
            <div>
              <span className="text-xs font-medium text-foreground">
                Drop PDFs here
              </span>
              <p className="text-[10px] text-muted-foreground mt-0.5">
                or click to browse
              </p>
            </div>
          </div>
        )}
      </div>

      {/* Upload result */}
      <AnimatePresence>
        {uploadResult && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            className="overflow-hidden"
          >
            <div
              className={cn(
                "mt-2 flex items-start gap-2 rounded-lg p-2.5 text-xs",
                uploadResult.success
                  ? "bg-green-500/10 text-green-600 dark:text-green-400"
                  : "bg-red-500/10 text-red-600 dark:text-red-400"
              )}
            >
              {uploadResult.success ? (
                <CheckCircle2 className="h-3.5 w-3.5 mt-0.5 shrink-0" />
              ) : (
                <AlertCircle className="h-3.5 w-3.5 mt-0.5 shrink-0" />
              )}
              <span className="flex-1">{uploadResult.message}</span>
              <button onClick={() => setUploadResult(null)}>
                <X className="h-3 w-3" />
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
