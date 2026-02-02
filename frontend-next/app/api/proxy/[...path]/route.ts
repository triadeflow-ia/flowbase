/**
 * Proxy para o backend FlowBase (evita CORS e expõe o backend apenas server-side).
 * O frontend chama /api/proxy/auth/register, /api/proxy/jobs, etc.
 * Esta rota encaminha para API_URL (variável de ambiente no Vercel).
 */

import { NextRequest, NextResponse } from "next/server";

const API_URL = process.env.API_URL || "https://flowbase-y89b.onrender.com";

function getBackendUrl(path: string[], request: NextRequest): string {
  const pathStr = path.join("/");
  const search = request.nextUrl.searchParams.toString();
  const url = `${API_URL.replace(/\/$/, "")}/${pathStr}`;
  return search ? `${url}?${search}` : url;
}

function buildHeaders(request: NextRequest, skipContentType = false): Headers {
  const headers = new Headers();
  const auth = request.headers.get("authorization");
  if (auth) {
    headers.set("Authorization", auth);
  }
  if (!skipContentType) {
    const contentType = request.headers.get("content-type");
    if (contentType) {
      headers.set("Content-Type", contentType);
    }
  }
  return headers;
}

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
) {
  const { path } = await params;
  const url = getBackendUrl(path, request);
  const headers = buildHeaders(request);
  try {
    const res = await fetch(url, { method: "GET", headers, cache: "no-store" });
    const data = await res.text();
    const contentType = res.headers.get("content-type") || "";
    try {
      if (contentType.includes("application/json")) {
        const json = JSON.parse(data);
        return NextResponse.json(json, { status: res.status });
      }
      const nextRes = new NextResponse(data, { status: res.status });
      nextRes.headers.set("Content-Type", contentType);
      const disposition = res.headers.get("content-disposition");
      if (disposition) nextRes.headers.set("Content-Disposition", disposition);
      return nextRes;
    } catch {
      return new NextResponse(data, { status: res.status });
    }
  } catch (e) {
    return NextResponse.json(
      { detail: String(e) },
      { status: 502 }
    );
  }
}

export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
) {
  const { path } = await params;
  const url = getBackendUrl(path, request);
  const contentType = request.headers.get("content-type") || "";
  const isMultipart = contentType.includes("multipart/form-data");
  const headers = buildHeaders(request, isMultipart);

  let body: BodyInit;
  if (isMultipart) {
    body = await request.formData();
  } else {
    body = await request.text();
  }

  try {
    const res = await fetch(url, {
      method: "POST",
      headers,
      body,
    });
    const data = await res.text();
    try {
      const json = JSON.parse(data);
      return NextResponse.json(json, { status: res.status });
    } catch {
      return new NextResponse(data, { status: res.status });
    }
  } catch (e) {
    return NextResponse.json(
      { detail: String(e) },
      { status: 502 }
    );
  }
}
