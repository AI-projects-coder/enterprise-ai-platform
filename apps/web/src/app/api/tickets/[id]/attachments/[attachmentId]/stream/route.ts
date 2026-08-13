import { cookies } from "next/headers";
import { NextResponse } from "next/server";
import { API_URL, getServerlessAuthHeaders } from "@/lib/api";

// Local-disk-only playback path (see support/router.py::_attachment_view_url
// — this URL is only ever handed out when there's no GCS bucket to sign a
// real URL against). Raw byte passthrough, not apiFetch, since apiFetch
// always JSON-parses the response and this one is an image/video file.
export async function GET(
  _req: Request,
  { params }: { params: Promise<{ id: string; attachmentId: string }> }
) {
  const { id, attachmentId } = await params;
  const cookieStore = await cookies();
  const token = cookieStore.get("access_token")?.value;

  if (!token) {
    return NextResponse.json({ detail: "Not authenticated" }, { status: 401 });
  }

  const serverlessAuthHeaders = await getServerlessAuthHeaders();
  const res = await fetch(`${API_URL}/tickets/${id}/attachments/${attachmentId}/stream`, {
    headers: { Authorization: `Bearer ${token}`, ...serverlessAuthHeaders },
  });

  if (!res.ok) {
    return NextResponse.json({ detail: "Stream failed" }, { status: res.status });
  }

  return new NextResponse(res.body, {
    headers: { "Content-Type": res.headers.get("Content-Type") ?? "application/octet-stream" },
  });
}
