const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:8000";

// 5-minute timeout for large file uploads
const UPLOAD_TIMEOUT_MS = 300_000;

export async function POST(request: Request) {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), UPLOAD_TIMEOUT_MS);

  try {
    const response = await fetch(`${BACKEND_URL}/upload`, {
      method: "POST",
      body: request.body,
      headers: {
        "content-type": request.headers.get("content-type") || "",
      },
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
      return Response.json({ detail: "Upload timed out" }, { status: 504 });
    }

    return Response.json({ detail: "Upload failed" }, { status: 502 });
  }
}
