const API_BASE = "http://localhost:8000/api";

async function fetchJson(url: string, options: RequestInit = {}) {
  const response = await fetch(url, options);
  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(body.detail || body.message || "Request failed");
  }
  return body;
}

export async function fetchConnections() {
  return fetchJson(`${API_BASE}/databases`);
}

export async function testConnection(connection: any) {
  return fetchJson(`${API_BASE}/databases/test`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(connection),
  });
}

export async function saveConnection(connection: any) {
  const payload = { ...connection };
  if (payload.id) {
    return fetchJson(`${API_BASE}/databases/${encodeURIComponent(payload.id)}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
  }

  return fetchJson(`${API_BASE}/databases`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export async function connectDatabase(connectionId: string) {
  return fetchJson(`${API_BASE}/databases/${encodeURIComponent(connectionId)}/connect`, {
    method: "PUT",
  });
}

export async function disconnectDatabase(connectionId: string) {
  return fetchJson(`${API_BASE}/databases/${encodeURIComponent(connectionId)}/disconnect`, {
    method: "PUT",
  });
}

export async function deleteConnection(connectionId: string) {
  return fetchJson(`${API_BASE}/databases/${connectionId}`, {
    method: "DELETE",
  });
}

export async function searchTables(connectionId: string, query: string) {
  return fetchJson(`${API_BASE}/tables/search?connection_id=${encodeURIComponent(connectionId)}&q=${encodeURIComponent(query)}`);
}

export async function listTables(connectionId: string) {
  return fetchJson(`${API_BASE}/tables?connection_id=${encodeURIComponent(connectionId)}`);
}

export async function getTableSchema(connectionId: string, tableName: string) {
  return fetchJson(`${API_BASE}/tables/${encodeURIComponent(tableName)}/schema?connection_id=${encodeURIComponent(connectionId)}`);
}

function resolveDownloadUrl(downloadUrl: string) {
  try {
    return new URL(downloadUrl, API_BASE).toString();
  } catch {
    return downloadUrl;
  }
}

export async function documentSingleTable(connectionId: string, tableName: string) {
  const result = await fetchJson(`${API_BASE}/documentation/table`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ connection_id: connectionId, table_name: tableName }),
  });
  if (result.download_url) {
    result.download_url = resolveDownloadUrl(result.download_url);
  }
  return result;
}

export async function uploadDocumentation(connectionId: string, file: File) {
  const formData = new FormData();
  formData.append("file", file);
  const result = await fetchJson(`${API_BASE}/documentation/upload?connection_id=${encodeURIComponent(connectionId)}`, {
    method: "POST",
    body: formData,
  });
  if (result.download_url) {
    result.download_url = resolveDownloadUrl(result.download_url);
  }
  return result;
}

export async function listJobs() {
  return fetchJson(`${API_BASE}/documentation/jobs`);
}

export async function publishGoogleSheet(jobId: string) {
  return fetchJson(`${API_BASE}/documentation/${encodeURIComponent(jobId)}/google-sheet`, {
    method: "POST",
  });
}

export function downloadJobUrl(jobId: string) {
  return `${API_BASE}/documentation/${encodeURIComponent(jobId)}/download`;
}
