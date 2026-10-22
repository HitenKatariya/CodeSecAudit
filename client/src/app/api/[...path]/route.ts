import { NextRequest } from "next/server";

import { proxyRequest } from "@/lib/proxy";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

type RouteContext = { params: { path: string[] } };

export function GET(request: NextRequest, context: RouteContext) {
  return proxyRequest(request, context.params.path, "/v1/");
}

export function POST(request: NextRequest, context: RouteContext) {
  return proxyRequest(request, context.params.path, "/v1/");
}

export function PUT(request: NextRequest, context: RouteContext) {
  return proxyRequest(request, context.params.path, "/v1/");
}

export function PATCH(request: NextRequest, context: RouteContext) {
  return proxyRequest(request, context.params.path, "/v1/");
}

export function DELETE(request: NextRequest, context: RouteContext) {
  return proxyRequest(request, context.params.path, "/v1/");
}
