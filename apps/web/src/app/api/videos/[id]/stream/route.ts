import { cookies } from "next/headers";
import { NextResponse } from "next/server";
import { API_URL, getServerlessAuthHeaders } from "@/lib/api";

// Local-disk-only playback path (see video/service.py::get_playback_url —
// this URL is only ever handed out when there's no GCS bucket to sign a
// real playback URL against). Raw byte passthrough, not apiFetch, since
// apiFetch always JSON-parses the response and this one is a video file.
export async function GET(_req: Request, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const cookieStore = await cookies();
  const token = cookieStore.get("access_token")?.value;

  if (!token) {
    return NextResponse.json({ detail: "Not authenticated" }, { status: 401 });
  }

  const serverlessAuthHeaders = await getServerlessAuthHeaders();
  const res = await fetch(`${API_URL}/videos/${id}/stream`, {
    headers: { Authorization: `Bearer ${token}`, ...serverlessAuthHeaders },
  });

  if (!res.ok) {
    return NextResponse.json({ detail: "Stream failed" }, { status: res.status });
  }

  return new NextResponse(res.body, {
    headers: { "Content-Type": res.headers.get("Content-Type") ?? "video/mp4" },
  });
}
