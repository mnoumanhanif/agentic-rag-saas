"use client";

import { useEffect, lazy, Suspense } from "react";
import { useChatStore } from "@/hooks/use-chat-store";
import { useAuthStore } from "@/hooks/use-auth-store";
import { Sidebar } from "@/components/layout/sidebar";
import { Header } from "@/components/layout/header";
import { ChatArea } from "@/components/chat/chat-area";
import { Skeleton } from "@/components/ui/skeleton";

const DashboardView = lazy(() => import("@/components/dashboard/dashboard-view"));
const DocumentsView = lazy(() => import("@/components/documents/documents-view"));
const AdminView = lazy(() => import("@/components/admin/admin-view"));
const AuthPage = lazy(() => import("@/components/auth/auth-page"));

function ViewSkeleton() {
  return (
    <div className="flex-1 p-6 space-y-4">
      <Skeleton className="h-8 w-48" />
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <Skeleton key={i} className="h-28 rounded-xl" />
        ))}
      </div>
      <Skeleton className="h-64 rounded-xl" />
    </div>
  );
}

export default function Home() {
  const { darkMode, activeView } = useChatStore();
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);

  useEffect(() => {
    document.documentElement.classList.toggle("dark", darkMode);
  }, [darkMode]);

  // Show auth page if not authenticated
  if (!isAuthenticated) {
    return (
      <Suspense fallback={<div className="min-h-screen bg-zinc-950" />}>
        <AuthPage />
      </Suspense>
    );
  }

  return (
    <div className="flex h-screen overflow-hidden bg-background text-foreground">
      <Sidebar />
      <div className="flex flex-1 flex-col min-w-0">
        <Header />
        {activeView === "chat" && <ChatArea />}
        {activeView === "dashboard" && (
          <Suspense fallback={<ViewSkeleton />}>
            <DashboardView />
          </Suspense>
        )}
        {activeView === "documents" && (
          <Suspense fallback={<ViewSkeleton />}>
            <DocumentsView />
          </Suspense>
        )}
        {activeView === "admin" && (
          <Suspense fallback={<ViewSkeleton />}>
            <AdminView />
          </Suspense>
        )}
      </div>
    </div>
  );
}
