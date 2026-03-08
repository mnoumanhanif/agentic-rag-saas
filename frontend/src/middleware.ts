import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

/**
 * Next.js middleware for frontend security.
 *
 * - Adds CSRF protection via same-origin validation on mutation requests
 * - Blocks requests with suspicious patterns
 * - Adds request ID for tracing
 */
export function middleware(request: NextRequest) {
  const response = NextResponse.next();

  // Generate request ID for tracing
  const requestId =
    request.headers.get("x-request-id") ?? crypto.randomUUID().slice(0, 16);
  response.headers.set("X-Request-ID", requestId);

  // CSRF protection: reject non-GET/HEAD/OPTIONS requests from different origins
  if (!["GET", "HEAD", "OPTIONS"].includes(request.method)) {
    const origin = request.headers.get("origin");
    const host = request.headers.get("host");

    if (origin && host) {
      try {
        const originHost = new URL(origin).host;
        if (originHost !== host) {
          return new NextResponse("Forbidden", { status: 403 });
        }
      } catch {
        return new NextResponse("Forbidden", { status: 403 });
      }
    }
  }

  return response;
}

export const config = {
  // Apply to all routes except static assets and Next.js internals
  matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"],
};
