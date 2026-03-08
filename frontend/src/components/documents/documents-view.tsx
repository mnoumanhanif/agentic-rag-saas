"use client";

import React, { useState, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  FileText,
  Upload,
  Trash2,
  RefreshCw,
  Search,
  ChevronDown,
  ChevronRight,
  Database,
  Hash,
  Calendar,
  HardDrive,
  Loader2,
  CheckCircle2,
  AlertCircle,
  X,
  FolderOpen,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { uploadFiles } from "@/lib/api";
import { cn } from "@/lib/utils";

interface DocumentRecord {
  id: string;
  filename: string;
  uploadedAt: Date;
  status: "indexed" | "processing" | "error";
}

export default function DocumentsView() {
  const [documents, setDocuments] = useState<DocumentRecord[]>([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [isUploading, setIsUploading] = useState(false);
  const [uploadResult, setUploadResult] = useState<{
    success: boolean;
    message: string;
  } | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [expandedDoc, setExpandedDoc] = useState<string | null>(null);

  const handleUpload = useCallback(async (files: File[]) => {
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

    // Add processing records
    const newDocs: DocumentRecord[] = pdfFiles.map((f) => ({
      id: crypto.randomUUID(),
      filename: f.name,
      uploadedAt: new Date(),
      status: "processing" as const,
    }));
    setDocuments((prev) => [...newDocs, ...prev]);

    try {
      const result = await uploadFiles(pdfFiles);
      // Mark as indexed
      setDocuments((prev) =>
        prev.map((d) =>
          newDocs.find((nd) => nd.id === d.id)
            ? { ...d, status: "indexed" as const }
            : d
        )
      );
      setUploadResult({ success: true, message: result.message });
    } catch (error) {
      // Mark as error
      setDocuments((prev) =>
        prev.map((d) =>
          newDocs.find((nd) => nd.id === d.id)
            ? { ...d, status: "error" as const }
            : d
        )
      );
      setUploadResult({
        success: false,
        message: error instanceof Error ? error.message : "Upload failed",
      });
    } finally {
      setIsUploading(false);
    }
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragging(false);
      handleUpload(Array.from(e.dataTransfer.files));
    },
    [handleUpload]
  );

  const handleInputChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      handleUpload(Array.from(e.target.files ?? []));
      e.target.value = "";
    },
    [handleUpload]
  );

  const removeDocument = (id: string) => {
    setDocuments((prev) => prev.filter((d) => d.id !== id));
  };

  const filteredDocs = searchQuery
    ? documents.filter((d) =>
        d.filename.toLowerCase().includes(searchQuery.toLowerCase())
      )
    : documents;

  return (
    <div className="flex-1 overflow-y-auto">
      <div className="mx-auto max-w-6xl p-6 space-y-6">
        {/* Title */}
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
        >
          <h1 className="text-2xl font-bold text-foreground">
            Document Explorer
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            Manage your indexed documents and knowledge base
          </p>
        </motion.div>

        <Tabs defaultValue="documents" className="space-y-4">
          <TabsList>
            <TabsTrigger value="documents">Documents</TabsTrigger>
            <TabsTrigger value="upload">Upload</TabsTrigger>
            <TabsTrigger value="vectordb">Vector Database</TabsTrigger>
          </TabsList>

          {/* Documents Tab */}
          <TabsContent value="documents" className="space-y-4">
            {/* Search */}
            <div className="relative">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search documents…"
                className="pl-9"
              />
            </div>

            {/* Document List */}
            {filteredDocs.length === 0 ? (
              <Card>
                <CardContent className="flex flex-col items-center justify-center py-12 text-center">
                  <FolderOpen className="h-12 w-12 text-muted-foreground/30 mb-4" />
                  <h3 className="text-lg font-medium text-foreground">
                    No documents indexed
                  </h3>
                  <p className="text-sm text-muted-foreground mt-1 max-w-sm">
                    Upload PDF documents to build your knowledge base. The
                    system will automatically index and create embeddings.
                  </p>
                </CardContent>
              </Card>
            ) : (
              <div className="grid gap-3">
                {filteredDocs.map((doc, i) => (
                  <motion.div
                    key={doc.id}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: i * 0.03 }}
                  >
                    <Card
                      className={cn(
                        "cursor-pointer transition-colors hover:border-primary/30",
                        expandedDoc === doc.id && "border-primary/50"
                      )}
                      onClick={() =>
                        setExpandedDoc(
                          expandedDoc === doc.id ? null : doc.id
                        )
                      }
                    >
                      <CardContent className="p-4">
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-3">
                            <div className="h-10 w-10 rounded-lg bg-primary/10 flex items-center justify-center">
                              <FileText className="h-5 w-5 text-primary" />
                            </div>
                            <div>
                              <h4 className="text-sm font-medium text-foreground">
                                {doc.filename}
                              </h4>
                              <div className="flex items-center gap-2 mt-0.5">
                                <span className="text-xs text-muted-foreground flex items-center gap-1">
                                  <Calendar className="h-3 w-3" />
                                  {doc.uploadedAt.toLocaleDateString()}
                                </span>
                              </div>
                            </div>
                          </div>
                          <div className="flex items-center gap-2">
                            <Badge
                              variant={
                                doc.status === "indexed"
                                  ? "secondary"
                                  : doc.status === "processing"
                                    ? "outline"
                                    : "destructive"
                              }
                              className="text-[10px]"
                            >
                              {doc.status === "processing" && (
                                <Loader2 className="h-3 w-3 animate-spin mr-1" />
                              )}
                              {doc.status}
                            </Badge>
                            {expandedDoc === doc.id ? (
                              <ChevronDown className="h-4 w-4 text-muted-foreground" />
                            ) : (
                              <ChevronRight className="h-4 w-4 text-muted-foreground" />
                            )}
                          </div>
                        </div>

                        <AnimatePresence>
                          {expandedDoc === doc.id && (
                            <motion.div
                              initial={{ height: 0, opacity: 0 }}
                              animate={{ height: "auto", opacity: 1 }}
                              exit={{ height: 0, opacity: 0 }}
                              transition={{ duration: 0.2 }}
                              className="overflow-hidden"
                            >
                              <div className="mt-4 pt-4 border-t space-y-3">
                                <div className="grid grid-cols-2 gap-4 text-xs">
                                  <div className="flex items-center gap-2">
                                    <Hash className="h-3.5 w-3.5 text-muted-foreground" />
                                    <span className="text-muted-foreground">
                                      Document ID:
                                    </span>
                                    <span className="font-mono">
                                      {doc.id.slice(0, 8)}
                                    </span>
                                  </div>
                                  <div className="flex items-center gap-2">
                                    <Database className="h-3.5 w-3.5 text-muted-foreground" />
                                    <span className="text-muted-foreground">
                                      Status:
                                    </span>
                                    <span>{doc.status}</span>
                                  </div>
                                </div>
                                <div className="flex items-center gap-2">
                                  <Button
                                    variant="outline"
                                    size="sm"
                                    className="text-xs gap-1.5"
                                    onClick={(e) => {
                                      e.stopPropagation();
                                    }}
                                  >
                                    <RefreshCw className="h-3 w-3" />
                                    Re-index
                                  </Button>
                                  <Button
                                    variant="outline"
                                    size="sm"
                                    className="text-xs gap-1.5 text-destructive hover:text-destructive"
                                    onClick={(e) => {
                                      e.stopPropagation();
                                      removeDocument(doc.id);
                                    }}
                                  >
                                    <Trash2 className="h-3 w-3" />
                                    Remove
                                  </Button>
                                </div>
                              </div>
                            </motion.div>
                          )}
                        </AnimatePresence>
                      </CardContent>
                    </Card>
                  </motion.div>
                ))}
              </div>
            )}
          </TabsContent>

          {/* Upload Tab */}
          <TabsContent value="upload" className="space-y-4">
            <Card>
              <CardContent className="p-6">
                <div
                  onDragOver={(e) => {
                    e.preventDefault();
                    setIsDragging(true);
                  }}
                  onDragLeave={() => setIsDragging(false)}
                  onDrop={handleDrop}
                  className={cn(
                    "relative rounded-xl border-2 border-dashed p-12 text-center transition-all duration-200",
                    isDragging
                      ? "border-primary bg-primary/5 scale-[1.01]"
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
                    <div className="flex flex-col items-center gap-3">
                      <Loader2 className="h-10 w-10 animate-spin text-primary" />
                      <div>
                        <p className="text-sm font-medium">
                          Processing documents…
                        </p>
                        <p className="text-xs text-muted-foreground mt-1">
                          Extracting text, creating chunks, and generating
                          embeddings
                        </p>
                      </div>
                    </div>
                  ) : (
                    <div className="flex flex-col items-center gap-3">
                      <div className="h-14 w-14 rounded-2xl bg-primary/10 flex items-center justify-center">
                        <Upload className="h-7 w-7 text-primary" />
                      </div>
                      <div>
                        <p className="text-sm font-medium">
                          Drop PDF files here or click to browse
                        </p>
                        <p className="text-xs text-muted-foreground mt-1">
                          Supports multiple PDF files. Documents will be
                          automatically indexed.
                        </p>
                      </div>
                    </div>
                  )}
                </div>

                {/* Upload result */}
                <AnimatePresence>
                  {uploadResult && (
                    <motion.div
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0, y: -10 }}
                      className="mt-4"
                    >
                      <div
                        className={cn(
                          "flex items-start gap-3 rounded-lg p-4",
                          uploadResult.success
                            ? "bg-green-500/10 text-green-600 dark:text-green-400"
                            : "bg-red-500/10 text-red-600 dark:text-red-400"
                        )}
                      >
                        {uploadResult.success ? (
                          <CheckCircle2 className="h-5 w-5 mt-0.5 shrink-0" />
                        ) : (
                          <AlertCircle className="h-5 w-5 mt-0.5 shrink-0" />
                        )}
                        <div className="flex-1">
                          <p className="text-sm font-medium">
                            {uploadResult.success
                              ? "Upload Successful"
                              : "Upload Failed"}
                          </p>
                          <p className="text-xs mt-0.5 opacity-80">
                            {uploadResult.message}
                          </p>
                        </div>
                        <button onClick={() => setUploadResult(null)}>
                          <X className="h-4 w-4" />
                        </button>
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Vector Database Tab */}
          <TabsContent value="vectordb" className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-2">
                    <Database className="h-4 w-4" />
                    Vector Store
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-2xl font-bold">FAISS</p>
                  <p className="text-xs text-muted-foreground mt-1">
                    Local vector index
                  </p>
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-2">
                    <HardDrive className="h-4 w-4" />
                    Embedding Model
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-lg font-bold">all-MiniLM-L6-v2</p>
                  <p className="text-xs text-muted-foreground mt-1">
                    384-dim sentence embeddings
                  </p>
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-2">
                    <FileText className="h-4 w-4" />
                    Documents
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-2xl font-bold">{documents.length}</p>
                  <p className="text-xs text-muted-foreground mt-1">
                    Tracked in session
                  </p>
                </CardContent>
              </Card>
            </div>

            <Card>
              <CardHeader>
                <CardTitle className="text-sm font-medium">
                  Vector Database Info
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3 text-sm">
                  <div className="flex items-center justify-between py-2 border-b">
                    <span className="text-muted-foreground">Index Type</span>
                    <span className="font-medium">FAISS (L2 distance)</span>
                  </div>
                  <div className="flex items-center justify-between py-2 border-b">
                    <span className="text-muted-foreground">
                      Embedding Dimensions
                    </span>
                    <span className="font-medium">384</span>
                  </div>
                  <div className="flex items-center justify-between py-2 border-b">
                    <span className="text-muted-foreground">
                      Similarity Metric
                    </span>
                    <span className="font-medium">Cosine Similarity</span>
                  </div>
                  <div className="flex items-center justify-between py-2">
                    <span className="text-muted-foreground">
                      Chunk Strategy
                    </span>
                    <span className="font-medium">
                      Recursive Text Splitting
                    </span>
                  </div>
                </div>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}
