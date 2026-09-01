/**
 * API proxy para o backend FastAPI.
 * Redireciona pedidos frontend para a API real em produção.
 */

import { type NextRequest, NextResponse } from "next/server";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ team_id: string; endpoint?: string[] }> }
) {
  const { team_id, endpoint } = await params;
  const endpointPath = endpoint?.join("/") || "";
  const url = `${API_URL}/api/teams/${team_id}/${endpointPath}`;

  try {
    const response = await fetch(url, {
      method: "GET",
      headers: {
        "Content-Type": "application/json",
        Authorization: request.headers.get("Authorization") || "",
      },
    });

    if (!response.ok) {
      return NextResponse.json({ error: "Backend error" }, { status: response.status });
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error("API proxy error:", error);
    return NextResponse.json({ error: "Failed to fetch from backend" }, { status: 500 });
  }
}
