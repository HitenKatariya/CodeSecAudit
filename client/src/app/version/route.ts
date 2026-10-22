import { NextResponse } from "next/server";

export async function GET() {
  return NextResponse.json({
    service: "client",
    version: "0.1.0",
    git_sha: process.env.GIT_SHA || "local",
    build_time: new Date().toISOString(),
  });
}
