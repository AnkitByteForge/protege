import { NextResponse, type NextRequest } from "next/server";

/**
 * The one same-origin boundary every P10 call crosses (see
 * `lib/protege-api-client.ts`'s module docstring for why: no CORS on
 * `services/session`, and the browser's native `EventSource` -- which
 * roadmap P10/P15 require for SSE -- cannot attach an `Authorization`
 * header at all). This route holds the only reference to the real backend
 * origin and attaches the bearer token server-side; the browser only ever
 * sees `/api/protege/*`.
 *
 * `PROTEGE_API_BASE_URL` is intentionally not `NEXT_PUBLIC_*` -- the real
 * session-service origin never needs to reach the client bundle.
 */
const API_BASE_URL = process.env.PROTEGE_API_BASE_URL ?? "http://127.0.0.1:8300";

const E2E_TOKEN_COOKIE = "protege_e2e_token";

async function resolveBearerToken(request: NextRequest): Promise<string | null> {
  // No real Clerk tenant exists in this environment's Playwright runs; the
  // E2E suite's global setup mints a token the same way
  // `services/session/tests/_auth_helpers.py` does for the backend's own
  // tests (a throwaway RSA keypair, real RS256 verification) and hands it
  // to the browser as this cookie -- see playwright.session.config.ts and
  // scripts/e2e-global-setup.ts. Checked first so a stray Clerk session in
  // the same browser profile never shadows an explicit E2E run.
  const e2eToken = request.cookies.get(E2E_TOKEN_COOKIE)?.value;
  if (e2eToken) return e2eToken;

  if (!process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY) return null;

  const { auth } = await import("@clerk/nextjs/server");
  const { getToken } = await auth();
  return getToken();
}

const HOP_BY_HOP_REQUEST_HEADERS = new Set(["host", "connection", "content-length", "cookie"]);

async function proxy(request: NextRequest, pathSegments: string[]): Promise<Response> {
  const token = await resolveBearerToken(request);
  if (!token) {
    return NextResponse.json(
      {
        type: "protege:unauthorized",
        title: "Unauthorized",
        status: 401,
        detail: "No verified session.",
        instance: request.nextUrl.pathname,
        child_safe_message: "You'll need a grown-up to help you sign in.",
      },
      { status: 401 },
    );
  }

  const upstreamHeaders = new Headers();
  for (const [key, value] of request.headers) {
    if (!HOP_BY_HOP_REQUEST_HEADERS.has(key.toLowerCase())) {
      upstreamHeaders.set(key, value);
    }
  }
  upstreamHeaders.set("authorization", `Bearer ${token}`);

  const hasBody = request.method !== "GET" && request.method !== "HEAD";
  const upstreamUrl = `${API_BASE_URL}/v1/${pathSegments.join("/")}${request.nextUrl.search}`;

  const upstream = await fetch(upstreamUrl, {
    method: request.method,
    headers: upstreamHeaders,
    body: hasBody ? await request.arrayBuffer() : undefined,
    // Streamed SSE responses must reach the browser as they arrive, not
    // once fully buffered -- `cache: "no-store"` keeps Next from trying to
    // cache/buffer a `text/event-stream` response.
    cache: "no-store",
  });

  const responseHeaders = new Headers(upstream.headers);
  responseHeaders.delete("content-encoding");
  responseHeaders.delete("content-length");

  return new Response(upstream.body, {
    status: upstream.status,
    headers: responseHeaders,
  });
}

interface RouteParams {
  params: Promise<{ path: string[] }>;
}

export async function GET(request: NextRequest, { params }: RouteParams): Promise<Response> {
  return proxy(request, (await params).path);
}

export async function POST(request: NextRequest, { params }: RouteParams): Promise<Response> {
  return proxy(request, (await params).path);
}

export const dynamic = "force-dynamic";
