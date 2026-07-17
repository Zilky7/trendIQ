import { NextResponse } from "next/server";

export const runtime = "nodejs";

export async function GET(_: Request, { params }: { params: Promise<{ symbol: string }> }) {
  const baseUrl = process.env.RESEARCH_SERVICE_URL;
  if (!baseUrl) return NextResponse.json({ detail: "research service is not configured" }, { status: 503 });

  const { symbol } = await params;
  try {
    const upstream = await fetch(`${baseUrl.replace(/\/$/, "")}/api/reports/${encodeURIComponent(symbol)}`, { cache: "no-store" });
    const content = await upstream.json();
    return NextResponse.json(content, { status: upstream.status });
  } catch {
    return NextResponse.json({ detail: "research service is unavailable" }, { status: 502 });
  }
}
