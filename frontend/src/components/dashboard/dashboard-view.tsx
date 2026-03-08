"use client";

import React, { useState, useEffect, useMemo } from "react";
import { motion } from "framer-motion";
import {
  MessageSquare,
  Clock,
  AlertTriangle,
  FileText,
  Activity,
  Zap,
  TrendingUp,
  Server,
} from "lucide-react";
import {
  AreaChart,
  Area,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
} from "recharts";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useChatStore } from "@/hooks/use-chat-store";
import { checkHealth, type HealthResponse } from "@/lib/api";

// Derive metrics from actual conversation data in the store
function useMetrics() {
  const { conversations } = useChatStore();
  const [health, setHealth] = useState<HealthResponse | null>(null);

  useEffect(() => {
    checkHealth()
      .then(setHealth)
      .catch(() => setHealth(null));
  }, []);

  return useMemo(() => {
    const totalQueries = conversations.reduce(
      (sum, c) => sum + c.messages.filter((m) => m.role === "user").length,
      0
    );
    const totalResponses = conversations.reduce(
      (sum, c) => sum + c.messages.filter((m) => m.role === "assistant" && !m.isLoading).length,
      0
    );
    const errors = conversations.reduce(
      (sum, c) =>
        sum +
        c.messages.filter(
          (m) => m.role === "assistant" && m.content.startsWith("⚠️")
        ).length,
      0
    );
    const reflectionCount = conversations.reduce(
      (sum, c) => sum + c.messages.filter((m) => m.reflection).length,
      0
    );
    const reflectionSum = conversations.reduce((sum, c) => {
      const scores = c.messages
        .filter((m) => m.reflection)
        .map((m) => m.reflection!.score);
      return sum + scores.reduce((a, b) => a + b, 0);
    }, 0);
    const avgReflection =
      reflectionCount > 0 ? reflectionSum / reflectionCount : 0;

    // Build daily chart data from conversations
    const dailyMap = new Map<string, { queries: number; errors: number }>();
    conversations.forEach((c) => {
      c.messages.forEach((m) => {
        if (m.role !== "user") return;
        const day = new Date(m.timestamp).toLocaleDateString("en-US", {
          month: "short",
          day: "numeric",
        });
        const entry = dailyMap.get(day) || { queries: 0, errors: 0 };
        entry.queries++;
        dailyMap.set(day, entry);
      });
      c.messages.forEach((m) => {
        if (m.role !== "assistant" || !m.content.startsWith("⚠️")) return;
        const day = new Date(m.timestamp).toLocaleDateString("en-US", {
          month: "short",
          day: "numeric",
        });
        const entry = dailyMap.get(day) || { queries: 0, errors: 0 };
        entry.errors++;
        dailyMap.set(day, entry);
      });
    });

    const chartData = Array.from(dailyMap.entries())
      .map(([date, data]) => ({ date, ...data }))
      .slice(-7);

    // Reflection score distribution
    const scoreDistribution = [
      { name: "Excellent (80-100%)", value: 0, color: "#22c55e" },
      { name: "Good (60-80%)", value: 0, color: "#eab308" },
      { name: "Fair (40-60%)", value: 0, color: "#f97316" },
      { name: "Poor (0-40%)", value: 0, color: "#ef4444" },
    ];
    conversations.forEach((c) => {
      c.messages.forEach((m) => {
        if (!m.reflection) return;
        const s = m.reflection.score;
        if (s >= 0.8) scoreDistribution[0].value++;
        else if (s >= 0.6) scoreDistribution[1].value++;
        else if (s >= 0.4) scoreDistribution[2].value++;
        else scoreDistribution[3].value++;
      });
    });

    return {
      totalQueries,
      totalResponses,
      errors,
      errorRate: totalQueries > 0 ? (errors / totalQueries) * 100 : 0,
      avgReflection,
      totalConversations: conversations.length,
      chartData,
      scoreDistribution: scoreDistribution.filter((d) => d.value > 0),
      health,
    };
  }, [conversations, health]);
}

function StatsCard({
  title,
  value,
  icon: Icon,
  description,
  trend,
  delay = 0,
}: {
  title: string;
  value: string | number;
  icon: React.ElementType;
  description: string;
  trend?: string;
  delay?: number;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, delay }}
    >
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium text-muted-foreground">
            {title}
          </CardTitle>
          <Icon className="h-4 w-4 text-muted-foreground" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">{value}</div>
          <div className="flex items-center gap-2 mt-1">
            <p className="text-xs text-muted-foreground">{description}</p>
            {trend && (
              <Badge variant="secondary" className="text-[10px] px-1.5 py-0">
                {trend}
              </Badge>
            )}
          </div>
        </CardContent>
      </Card>
    </motion.div>
  );
}

export default function DashboardView() {
  const metrics = useMetrics();

  return (
    <div className="flex-1 overflow-y-auto">
      <div className="mx-auto max-w-6xl p-6 space-y-6">
        {/* Title */}
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex items-center justify-between"
        >
          <div>
            <h1 className="text-2xl font-bold text-foreground">
              System Dashboard
            </h1>
            <p className="text-sm text-muted-foreground mt-1">
              Monitor your Agentic RAG system performance and analytics
            </p>
          </div>
          <div className="flex items-center gap-2">
            {metrics.health && (
              <Badge
                variant={
                  metrics.health.status === "healthy"
                    ? "secondary"
                    : "destructive"
                }
                className="gap-1"
              >
                <div
                  className={`h-1.5 w-1.5 rounded-full ${metrics.health.status === "healthy" ? "bg-green-500" : "bg-red-500"}`}
                />
                {metrics.health.status}
              </Badge>
            )}
            {metrics.health?.version && (
              <Badge variant="outline" className="text-xs">
                v{metrics.health.version}
              </Badge>
            )}
          </div>
        </motion.div>

        {/* Stats Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <StatsCard
            title="Total Queries"
            value={metrics.totalQueries}
            icon={MessageSquare}
            description="Questions asked"
            delay={0}
          />
          <StatsCard
            title="Conversations"
            value={metrics.totalConversations}
            icon={Activity}
            description="Active sessions"
            delay={0.05}
          />
          <StatsCard
            title="Error Rate"
            value={`${metrics.errorRate.toFixed(1)}%`}
            icon={AlertTriangle}
            description={`${metrics.errors} errors`}
            delay={0.1}
          />
          <StatsCard
            title="Avg Quality"
            value={`${(metrics.avgReflection * 100).toFixed(0)}%`}
            icon={Zap}
            description="Reflection score"
            delay={0.15}
          />
        </div>

        {/* Charts */}
        <Tabs defaultValue="activity" className="space-y-4">
          <TabsList>
            <TabsTrigger value="activity">Query Activity</TabsTrigger>
            <TabsTrigger value="quality">Response Quality</TabsTrigger>
            <TabsTrigger value="system">System Status</TabsTrigger>
          </TabsList>

          <TabsContent value="activity">
            <Card>
              <CardHeader>
                <CardTitle className="text-sm font-medium flex items-center gap-2">
                  <TrendingUp className="h-4 w-4" />
                  Query Activity
                </CardTitle>
              </CardHeader>
              <CardContent>
                {metrics.chartData.length > 0 ? (
                  <div className="h-[300px]">
                    <ResponsiveContainer width="100%" height="100%">
                      <AreaChart data={metrics.chartData}>
                        <defs>
                          <linearGradient
                            id="colorQueries"
                            x1="0"
                            y1="0"
                            x2="0"
                            y2="1"
                          >
                            <stop
                              offset="5%"
                              stopColor="#7c3aed"
                              stopOpacity={0.3}
                            />
                            <stop
                              offset="95%"
                              stopColor="#7c3aed"
                              stopOpacity={0}
                            />
                          </linearGradient>
                        </defs>
                        <CartesianGrid
                          strokeDasharray="3 3"
                          className="stroke-border"
                        />
                        <XAxis
                          dataKey="date"
                          className="text-xs"
                          tick={{ fill: "var(--muted-foreground)", fontSize: 12 }}
                        />
                        <YAxis
                          className="text-xs"
                          tick={{ fill: "var(--muted-foreground)", fontSize: 12 }}
                        />
                        <Tooltip
                          contentStyle={{
                            backgroundColor: "var(--card)",
                            border: "1px solid var(--border)",
                            borderRadius: "8px",
                            color: "var(--foreground)",
                          }}
                        />
                        <Area
                          type="monotone"
                          dataKey="queries"
                          stroke="#7c3aed"
                          fill="url(#colorQueries)"
                          strokeWidth={2}
                        />
                        <Area
                          type="monotone"
                          dataKey="errors"
                          stroke="#ef4444"
                          fill="transparent"
                          strokeWidth={1}
                          strokeDasharray="4 4"
                        />
                      </AreaChart>
                    </ResponsiveContainer>
                  </div>
                ) : (
                  <div className="h-[300px] flex items-center justify-center text-muted-foreground">
                    <div className="text-center space-y-2">
                      <MessageSquare className="h-8 w-8 mx-auto opacity-50" />
                      <p className="text-sm">
                        No query data yet. Start a conversation to see
                        analytics.
                      </p>
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="quality">
            <Card>
              <CardHeader>
                <CardTitle className="text-sm font-medium flex items-center gap-2">
                  <Zap className="h-4 w-4" />
                  Response Quality Distribution
                </CardTitle>
              </CardHeader>
              <CardContent>
                {metrics.scoreDistribution.length > 0 ? (
                  <div className="h-[300px] flex items-center justify-center">
                    <ResponsiveContainer width="100%" height="100%">
                      <PieChart>
                        <Pie
                          data={metrics.scoreDistribution}
                          cx="50%"
                          cy="50%"
                          innerRadius={60}
                          outerRadius={100}
                          paddingAngle={5}
                          dataKey="value"
                        >
                          {metrics.scoreDistribution.map((entry, index) => (
                            <Cell key={`cell-${index}`} fill={entry.color} />
                          ))}
                        </Pie>
                        <Tooltip
                          contentStyle={{
                            backgroundColor: "var(--card)",
                            border: "1px solid var(--border)",
                            borderRadius: "8px",
                            color: "var(--foreground)",
                          }}
                        />
                      </PieChart>
                    </ResponsiveContainer>
                  </div>
                ) : (
                  <div className="h-[300px] flex items-center justify-center text-muted-foreground">
                    <div className="text-center space-y-2">
                      <Zap className="h-8 w-8 mx-auto opacity-50" />
                      <p className="text-sm">
                        No quality data yet. Responses with reflection scores
                        will appear here.
                      </p>
                    </div>
                  </div>
                )}
                {metrics.scoreDistribution.length > 0 && (
                  <div className="mt-4 grid grid-cols-2 gap-2">
                    {metrics.scoreDistribution.map((entry) => (
                      <div
                        key={entry.name}
                        className="flex items-center gap-2 text-xs"
                      >
                        <div
                          className="h-3 w-3 rounded-full"
                          style={{ backgroundColor: entry.color }}
                        />
                        <span className="text-muted-foreground">
                          {entry.name}: {entry.value}
                        </span>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="system">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <Card>
                <CardHeader>
                  <CardTitle className="text-sm font-medium flex items-center gap-2">
                    <Server className="h-4 w-4" />
                    Backend Status
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  <StatusRow
                    label="API Server"
                    status={metrics.health ? "healthy" : "offline"}
                  />
                  <StatusRow
                    label="LLM Provider"
                    status={
                      metrics.health?.llm_available ? "ready" : "unavailable"
                    }
                  />
                  <StatusRow
                    label="Vector Store"
                    status={
                      metrics.health?.vector_store_loaded
                        ? "loaded"
                        : "empty"
                    }
                  />
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle className="text-sm font-medium flex items-center gap-2">
                    <FileText className="h-4 w-4" />
                    Session Summary
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  <SummaryRow
                    label="Conversations"
                    value={String(metrics.totalConversations)}
                  />
                  <SummaryRow
                    label="Total Messages"
                    value={String(metrics.totalQueries + metrics.totalResponses)}
                  />
                  <SummaryRow
                    label="Errors"
                    value={String(metrics.errors)}
                  />
                  <SummaryRow
                    label="Avg Quality Score"
                    value={`${(metrics.avgReflection * 100).toFixed(0)}%`}
                  />
                </CardContent>
              </Card>
            </div>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}

function StatusRow({
  label,
  status,
}: {
  label: string;
  status: string;
}) {
  const isGood = ["healthy", "ready", "loaded"].includes(status);
  return (
    <div className="flex items-center justify-between text-sm">
      <span className="text-muted-foreground">{label}</span>
      <Badge
        variant={isGood ? "secondary" : "destructive"}
        className="text-[10px]"
      >
        <div
          className={`h-1.5 w-1.5 rounded-full mr-1 ${isGood ? "bg-green-500" : "bg-red-500"}`}
        />
        {status}
      </Badge>
    </div>
  );
}

function SummaryRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between text-sm">
      <span className="text-muted-foreground">{label}</span>
      <span className="font-medium text-foreground">{value}</span>
    </div>
  );
}
