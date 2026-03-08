"use client";

import { useEffect, useState } from "react";
import { getSystemMetrics, type SystemMetrics } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

export default function AdminView() {
  const [metrics, setMetrics] = useState<SystemMetrics | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getSystemMetrics()
      .then(setMetrics)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="flex-1 p-6">
        <div className="animate-pulse space-y-4">
          <div className="h-8 w-48 bg-zinc-800 rounded" />
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {Array.from({ length: 8 }).map((_, i) => (
              <div key={i} className="h-28 bg-zinc-800 rounded-xl" />
            ))}
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex-1 p-6">
        <div className="rounded-xl border border-red-500/20 bg-red-500/5 p-6 text-red-400">
          <h3 className="font-semibold mb-2">Access Denied</h3>
          <p className="text-sm">{error}</p>
        </div>
      </div>
    );
  }

  if (!metrics) return null;

  const cards = [
    { title: "Total Users", value: metrics.total_users, icon: "👥", color: "text-blue-400" },
    { title: "Active Users", value: metrics.active_users, icon: "✅", color: "text-green-400" },
    { title: "Knowledge Bases", value: metrics.total_knowledge_bases, icon: "📚", color: "text-violet-400" },
    { title: "Documents", value: metrics.total_documents, icon: "📄", color: "text-amber-400" },
    { title: "Conversations", value: metrics.total_conversations, icon: "💬", color: "text-cyan-400" },
    { title: "Messages", value: metrics.total_messages, icon: "📨", color: "text-pink-400" },
    { title: "Queries (24h)", value: metrics.total_queries_24h, icon: "🔍", color: "text-orange-400" },
    { title: "Avg Latency", value: `${metrics.avg_latency_ms}ms`, icon: "⚡", color: "text-yellow-400" },
    { title: "Total Tokens", value: metrics.total_tokens_used.toLocaleString(), icon: "🔢", color: "text-emerald-400" },
    { title: "Error Rate", value: `${(metrics.error_rate * 100).toFixed(2)}%`, icon: "⚠️", color: metrics.error_rate > 0.05 ? "text-red-400" : "text-green-400" },
  ];

  return (
    <div className="flex-1 overflow-y-auto p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Admin Dashboard</h1>
          <p className="text-zinc-400 text-sm mt-1">System-wide metrics and management</p>
        </div>
        <Badge variant="outline" className="border-violet-500/50 text-violet-400">
          Admin
        </Badge>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-4">
        {cards.map((card) => (
          <Card key={card.title} className="bg-zinc-900/50 border-zinc-800">
            <CardHeader className="pb-2">
              <CardTitle className="text-xs font-medium text-zinc-400 flex items-center gap-2">
                <span>{card.icon}</span>
                {card.title}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className={`text-2xl font-bold ${card.color}`}>{card.value}</p>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* System Health */}
      <Card className="bg-zinc-900/50 border-zinc-800">
        <CardHeader>
          <CardTitle className="text-white">System Health</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="flex items-center justify-between py-2 border-b border-zinc-800">
            <span className="text-zinc-400">Error Rate</span>
            <Badge variant={metrics.error_rate < 0.01 ? "default" : "destructive"}>
              {metrics.error_rate < 0.01 ? "Healthy" : "Degraded"}
            </Badge>
          </div>
          <div className="flex items-center justify-between py-2 border-b border-zinc-800">
            <span className="text-zinc-400">Avg Query Latency</span>
            <Badge variant={metrics.avg_latency_ms < 5000 ? "default" : "destructive"}>
              {metrics.avg_latency_ms < 5000 ? "Normal" : "Slow"}
            </Badge>
          </div>
          <div className="flex items-center justify-between py-2">
            <span className="text-zinc-400">Active Users / Total</span>
            <span className="text-white font-medium">
              {metrics.active_users} / {metrics.total_users}
            </span>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
