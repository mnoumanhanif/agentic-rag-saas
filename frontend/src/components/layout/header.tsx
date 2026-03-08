"use client";

import React, { useEffect, useState } from "react";
import {
  PanelLeft,
  Sun,
  Moon,
  Activity,
  Wifi,
  WifiOff,
  LayoutDashboard,
  MessageSquare,
  FolderOpen,
  Brain,
} from "lucide-react";
import { useChatStore } from "@/hooks/use-chat-store";
import { checkHealth, type HealthResponse } from "@/lib/api";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";

export function Header() {
  const {
    sidebarOpen,
    toggleSidebar,
    darkMode,
    toggleDarkMode,
    showReasoning,
    toggleReasoning,
    activeView,
    setActiveView,
  } = useChatStore();
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [isConnected, setIsConnected] = useState(false);

  useEffect(() => {
    const fetchHealth = async () => {
      try {
        const data = await checkHealth();
        setHealth(data);
        setIsConnected(true);
      } catch {
        setIsConnected(false);
        setHealth(null);
      }
    };

    fetchHealth();
    const interval = setInterval(fetchHealth, 30000);
    return () => clearInterval(interval);
  }, []);

  const navItems = [
    { id: "chat" as const, label: "Chat", icon: MessageSquare },
    { id: "dashboard" as const, label: "Dashboard", icon: LayoutDashboard },
    { id: "documents" as const, label: "Documents", icon: FolderOpen },
  ];

  return (
    <header className="flex h-14 items-center justify-between border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60 px-4">
      <div className="flex items-center gap-2">
        {!sidebarOpen && (
          <Button
            variant="ghost"
            size="icon"
            onClick={toggleSidebar}
            className="h-8 w-8"
          >
            <PanelLeft className="h-4 w-4" />
          </Button>
        )}
        <div className="flex items-center gap-2">
          <div className="h-7 w-7 rounded-lg bg-gradient-to-br from-violet-500 to-indigo-600 flex items-center justify-center">
            <Activity className="h-3.5 w-3.5 text-white" />
          </div>
          <span className="text-sm font-semibold hidden sm:inline">
            Agentic RAG
          </span>
        </div>

        {/* Navigation */}
        <nav className="hidden md:flex items-center ml-4 gap-1">
          {navItems.map((item) => (
            <Button
              key={item.id}
              variant={activeView === item.id ? "secondary" : "ghost"}
              size="sm"
              onClick={() => setActiveView(item.id)}
              className={cn(
                "gap-1.5 h-8 text-xs",
                activeView === item.id && "bg-accent font-medium"
              )}
            >
              <item.icon className="h-3.5 w-3.5" />
              {item.label}
            </Button>
          ))}
        </nav>
      </div>

      <div className="flex items-center gap-2">
        {/* Agent Reasoning Toggle */}
        <Button
          variant={showReasoning ? "secondary" : "ghost"}
          size="sm"
          onClick={toggleReasoning}
          className={cn(
            "gap-1.5 h-8 text-xs hidden sm:flex",
            showReasoning &&
              "bg-violet-500/10 text-violet-600 dark:text-violet-400"
          )}
        >
          <Brain className="h-3.5 w-3.5" />
          <span className="hidden lg:inline">Reasoning</span>
        </Button>

        {/* Connection status */}
        <div
          className={cn(
            "flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium",
            isConnected
              ? "bg-green-500/10 text-green-600 dark:text-green-400"
              : "bg-red-500/10 text-red-600 dark:text-red-400"
          )}
        >
          {isConnected ? (
            <Wifi className="h-3 w-3" />
          ) : (
            <WifiOff className="h-3 w-3" />
          )}
          <span className="hidden sm:inline">
            {isConnected ? "Connected" : "Offline"}
          </span>
        </div>

        {/* LLM status */}
        {health && (
          <div
            className={cn(
              "hidden sm:flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium",
              health.llm_available
                ? "bg-green-500/10 text-green-600 dark:text-green-400"
                : "bg-yellow-500/10 text-yellow-600 dark:text-yellow-400"
            )}
          >
            <div
              className={cn(
                "h-1.5 w-1.5 rounded-full",
                health.llm_available ? "bg-green-500" : "bg-yellow-500"
              )}
            />
            {health.llm_available ? "LLM Ready" : "No LLM"}
          </div>
        )}

        {/* Mobile nav */}
        <div className="flex md:hidden items-center gap-1">
          {navItems.map((item) => (
            <Button
              key={item.id}
              variant={activeView === item.id ? "secondary" : "ghost"}
              size="icon"
              onClick={() => setActiveView(item.id)}
              className="h-8 w-8"
            >
              <item.icon className="h-4 w-4" />
            </Button>
          ))}
        </div>

        {/* Dark mode toggle */}
        <Button
          variant="ghost"
          size="icon"
          onClick={toggleDarkMode}
          className="h-8 w-8"
        >
          {darkMode ? (
            <Sun className="h-4 w-4" />
          ) : (
            <Moon className="h-4 w-4" />
          )}
        </Button>
      </div>
    </header>
  );
}
