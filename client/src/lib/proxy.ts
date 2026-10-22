import { NextRequest, NextResponse } from "next/server";

function normalizeBase(value: string | undefined, fallback: string): string {
  const raw = (value || fallback).trim();
  const withScheme = /^https?:\/\//i.test(raw) ? raw : `http://${raw}`;
  return withScheme.replace(/\/+$/, "");
}

export function mainServerBase(): string {
  return normalizeBase(process.env.MAIN_SERVER_URL, "http://main-server:8000");
}

/**
 * Forward a browser request to the main-server.
 *
 * This is a runtime proxy (not a next.config rewrite) so MAIN_SERVER_URL is
 * read from the environment when the container starts. Next rewrites are baked
 * into the build, which breaks Render deployments where URLs are only known at
 * runtime.
 */
export async function proxyRequest(
  request: NextRequest,
  path: string[],
  prefix: "/v1/" | "/"
): Promise<NextResponse> {
  const target = `${mainServerBase()}${prefix}${path.join("/")}${request.nextUrl.search}`;

  const headers = new Headers(request.headers);
  for (const hopByHop of [
    "host",
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailer",
    "transfer-encoding",
    "upgrade",
    "content-length",
  ]) {
    headers.delete(hopByHop);
  }

  const init: RequestInit = {
    method: request.method,
    headers,
    redirect: "manual",
    cache: "no-store",
  };

  if (request.method !== "GET" && request.method !== "HEAD") {
    init.body = new Uint8Array(await request.arrayBuffer());
  }

  let upstream: Response;
  try {
    upstream = await fetch(target, init);
  } catch (error) {
    const message = error instanceof Error ? error.message : "unknown error";
    return NextResponse.json(
      { detail: `Upstream service unreachable: ${message}` },
      { status: 502 }
    );
  }

  const responseHeaders = new Headers();
  const skipResponseHeaders = new Set([
    "set-cookie",
    "content-length",
    "content-encoding",
    "transfer-encoding",
    "connection",
    "keep-alive",
  ]);
  upstream.headers.forEach((value, key) => {
    if (skipResponseHeaders.has(key.toLowerCase())) {
      return;
    }
    responseHeaders.set(key, value);
  });

  const getSetCookie = (upstream.headers as Headers & { getSetCookie?: () => string[] })
    .getSetCookie;
  const setCookies = typeof getSetCookie === "function" ? getSetCookie.call(upstream.headers) : [];
  if (setCookies.length > 0) {
    for (const cookie of setCookies) {
      responseHeaders.append("set-cookie", cookie);
    }
  } else {
    const singleCookie = upstream.headers.get("set-cookie");
    if (singleCookie) {
      responseHeaders.append("set-cookie", singleCookie);
    }
  }

  return new NextResponse(upstream.body, {
    status: upstream.status,
    statusText: upstream.statusText,
    headers: responseHeaders,
  });
}
