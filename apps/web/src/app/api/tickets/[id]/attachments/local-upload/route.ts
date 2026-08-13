import { cookies } from "next/headers";
import { NextRequest, NextResponse } from "next/server";
import { apiFetch, ApiError } from "@/lib/api";

export async function POST(req: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const cookieStore = await cookies();
  const token = cookieStore.get("access_token")?.value;
  if (!token) return NextResponse.json({ detail: "Not authenticated" }, { status: 401 });

  const formData = await req.formData();
  try {
    const attachment = await apiFetch(`/tickets/${id}/attachments/local-upload`, {
      method: "POST",
      body: formData,
      headers: { Authorization: `Bearer ${token}` },
    });
    return NextResponse.json(attachment, { status: 201 });
  } catch (err) {
    if (err instanceof ApiError) return NextResponse.json({ detail: err.message }, { status: err.status });
    throw err;
  }
}
