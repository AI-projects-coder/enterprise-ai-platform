const API_URL = process.env.API_INTERNAL_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

// api is a private Cloud Run service (--no-allow-unauthenticated) — this
// fetches a Google-signed ID token from the Cloud Run metadata server so
// Cloud Run's own IAM layer lets the request through. K_SERVICE only exists
// on Cloud Run, never in local dev, so local docker-compose is unaffected
// (api there has no IAM check at all). Sent via X-Serverless-Authorization,
// not Authorization — that header is reserved for the end user's JWT, which
// apiFetch callers set via init.headers; Cloud Run strips
// X-Serverless-Authorization before it ever reaches our container, so
// there's no collision on either side.
async function getIdentityToken(): Promise<string | null> {
  if (!process.env.K_SERVICE) return null;

  const metadataUrl = `http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/identity?audience=${encodeURIComponent(API_URL)}`;
  const res = await fetch(metadataUrl, { headers: { "Metadata-Flavor": "Google" } });
  if (!res.ok) {
    throw new Error(`Failed to fetch Cloud Run identity token: ${res.status}`);
  }
  return res.text();
}

export async function apiFetch(path: string, init?: RequestInit) {
  const identityToken = await getIdentityToken();
  // FormData (video upload) needs its own auto-generated multipart
  // boundary in Content-Type — setting "application/json" here would
  // break it, so this is the one case where we let fetch set it itself.
  const isFormData = init?.body instanceof FormData;

  const res = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: {
      ...(isFormData ? {} : { "Content-Type": "application/json" }),
      ...(identityToken ? { "X-Serverless-Authorization": `Bearer ${identityToken}` } : {}),
      ...init?.headers,
    },
  });

  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new ApiError(res.status, body.detail ?? "Request failed");
  }

  if (res.status === 204) {
    return null;
  }

  return res.json();
}
