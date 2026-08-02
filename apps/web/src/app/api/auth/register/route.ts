import { NextRequest, NextResponse } from "next/server";
import { apiFetch, ApiError } from "@/lib/api";

export async function POST(req: NextRequest) {
  const body = await req.json();

  try {
    const user = await apiFetch("/auth/register", {
      method: "POST",
      body: JSON.stringify(body),
    });
    return NextResponse.json(user, { status: 201 });
  } catch (err) {
    if (err instanceof ApiError) {
      return NextResponse.json({ detail: err.message }, { status: err.status });
    }
    throw err;
  }
}
