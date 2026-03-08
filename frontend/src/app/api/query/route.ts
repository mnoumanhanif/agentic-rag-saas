const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:8000";

// 5-minute timeout for complex RAG queries
const QUERY_TIMEOUT_MS = 300_000;

export async function POST(request: Request) {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), QUERY_TIMEOUT_MS);

  try {
    const response = await fetch(`${BACKEND_URL}/query`, {
      method: "POST",
      body: request.body,
      headers: { "content-type": "application/json" },
      signal: controller.signal,
      // @ts-expect-error -- Node.js fetch requires duplex for streaming body
      duplex: "half",
    });

    clearTimeout(timeoutId);

    return new Response(response.body, {
      status: response.status,
      headers: {
        "content-type":
          response.headers.get("content-type") || "application/json",
      },
    });
  } catch (error: unknown) {
    clearTimeout(timeoutId);

    if (error instanceof Error && error.name === "AbortError") {
      return Response.json({ detail: "Query timed out" }, { status: 504 });
    }

    return Response.json({ detail: "Query failed" }, { status: 502 });
  }
}
