import { ApiClient, createApi } from "@commerce-os/api-client";

export function backendUrl(): string {
  return (process.env.BACKEND_URL ?? "http://localhost:8000").replace(/\/+$/, "");
}

/** Server-side client for the backend; no bearer token (BFF session routes only). */
export function backendApi() {
  return createApi(new ApiClient({ baseUrl: `${backendUrl()}/api/v1` }));
}
