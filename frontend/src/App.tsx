import { useEffect, useMemo, useState } from "react";
import {
  fetchConnections,
  testConnection,
  saveConnection,
  deleteConnection,
  searchTables,
  getTableSchema,
  uploadDocumentation,
  documentSingleTable,
  listJobs,
  downloadJobUrl,
  publishGoogleSheet,
} from "./services/api";

interface Connection {
  id: string;
  name: string;
  type: string;
  host: string;
  port: number;
  database: string;
  schema: string;
  created_at: string;
}

interface TableColumn {
  column_name: string;
  ordinal_position: number;
  data_type: string;
  is_nullable: boolean;
  column_default?: string | null;
  column_comment?: string | null;
  is_primary: boolean;
  foreign_key?: {
    referenced_table?: string;
    referenced_column?: string;
    constraint_name?: string;
  } | null;
}

interface JobSummary {
  total: number;
  processed: number;
  not_found: number;
  found: string[];
  not_found_list: string[];
}

function App() {
  const [connections, setConnections] = useState<Connection[]>([]);
  const [selectedConnection, setSelectedConnection] = useState<string>("");
  const [showAddDatabase, setShowAddDatabase] = useState(false);
  const [connectionForm, setConnectionForm] = useState({
    name: "",
    type: "postgresql",
    host: "",
    port: 5432,
    database: "",
    username: "",
    password: "",
    schema: "public",
  });
  const [testStatus, setTestStatus] = useState<string>("");
  const [searchTerm, setSearchTerm] = useState("");
  const [searchResults, setSearchResults] = useState<string[]>([]);
  const [selectedTable, setSelectedTable] = useState<string>("");
  const [schema, setSchema] = useState<TableColumn[]>([]);
  const [tableInfo, setTableInfo] = useState({ table_name: "", connection_name: "", schema: "", column_count: 0 });
  const [searchLoading, setSearchLoading] = useState(false);
  const [schemaLoading, setSchemaLoading] = useState(false);
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [uploadStatus, setUploadStatus] = useState<string>("");
  const [uploadSummary, setUploadSummary] = useState<JobSummary | null>(null);
  const [jobs, setJobs] = useState<any[]>([]);
  const [errorMessage, setErrorMessage] = useState<string>("");
  const [downloadLink, setDownloadLink] = useState<string>("");
  const [googleSheetStatus, setGoogleSheetStatus] = useState<string>("");

  const selectedConnectionMeta = useMemo(
    () => connections.find((item) => item.id === selectedConnection),
    [connections, selectedConnection]
  );

  useEffect(() => {
    fetchConnections().then((items) => {
      setConnections(items);
      if (!selectedConnection && items.length > 0) {
        setSelectedConnection(items[0].id);
      }
    });
    listJobs().then((data) => setJobs(data.jobs || []));
  }, []);

  useEffect(() => {
    if (!searchTerm || !selectedConnection) {
      setSearchResults([]);
      return;
    }
    const timer = window.setTimeout(() => {
      setSearchLoading(true);
      searchTables(selectedConnection, searchTerm)
        .then((data) => setSearchResults(data.tables || []))
        .catch(() => setErrorMessage("Unable to search tables. Please try again."))
        .finally(() => setSearchLoading(false));
    }, 400);
    return () => window.clearTimeout(timer);
  }, [searchTerm, selectedConnection]);

  const refreshConnections = () => {
    fetchConnections().then((items) => {
      setConnections(items);
      if (!selectedConnection && items.length > 0) {
        setSelectedConnection(items[0].id);
      }
    });
  };

  const handleTestConnection = async () => {
    setTestStatus("Testing connection...");
    try {
      await testConnection(connectionForm);
      setTestStatus("✓ Database connection successful");
    } catch {
      setTestStatus("✕ Unable to connect to database. Please verify the connection details.");
    }
  };

  const handleSaveConnection = async () => {
    setTestStatus("Saving connection...");
    try {
      const result = await saveConnection(connectionForm);
      setConnections((prev) => [...prev, result]);
      setSelectedConnection(result.id);
      setShowAddDatabase(false);
      setConnectionForm({ name: "", type: "postgresql", host: "", port: 5432, database: "", username: "", password: "", schema: "public" });
      setTestStatus("");
    } catch (error: any) {
      setErrorMessage(error?.message || "Unable to save database connection.");
      setTestStatus("");
    }
  };

  const handleSelectTable = (table: string) => {
    setSelectedTable(table);
    setSearchTerm(table);
  };

  const loadTableSchema = async () => {
    if (!selectedConnection || !selectedTable) {
      setErrorMessage("Please select a database and a table.");
      return;
    }
    setSchemaLoading(true);
    setErrorMessage("");
    try {
      const data = await getTableSchema(selectedConnection, selectedTable);
      setTableInfo(data);
      setSchema(data.columns || []);
      const download = await documentSingleTable(selectedConnection, selectedTable);
      setDownloadLink(download.download_url);
    } catch (error: any) {
      setErrorMessage(error?.message || "Unable to load table schema.");
    } finally {
      setSchemaLoading(false);
    }
  };

  const handleUpload = async () => {
    if (!selectedConnection || !uploadFile) {
      setErrorMessage("Please select a database and a file to upload.");
      return;
    }
    setUploadStatus("Processing uploaded file...");
    setErrorMessage("");
    try {
      const result = await uploadDocumentation(selectedConnection, uploadFile);
      setUploadSummary(result.summary);
      setDownloadLink(result.download_url);
      setUploadStatus("Bulk documentation completed.");
    } catch (error: any) {
      setErrorMessage(error?.message || "Unable to process uploaded file.");
      setUploadStatus("");
    }
  };

  const handlePublishGoogleSheet = async () => {
    if (!downloadLink) {
      setErrorMessage("No documentation job is available for Google Sheets publishing.");
      return;
    }
    setGoogleSheetStatus("Generating Google Sheet...");
    try {
      const jobId = downloadLink.split("/").pop() || "";
      await publishGoogleSheet(jobId);
      setGoogleSheetStatus("Google Sheet generated successfully.");
    } catch {
      setGoogleSheetStatus("Unable to publish to Google Sheets.");
    }
  };

  return (
    <div className="app-shell">
      <header className="topbar">
        <div>
          <p className="eyebrow">Database Schema Documentation</p>
          <h1>Schema documentation portal</h1>
          <p>Manage database connections, search tables, and generate schema documentation.</p>
        </div>
        <button className="primary-button" onClick={() => setShowAddDatabase(true)}>
          + Add Database
        </button>
      </header>

      <section className="panel">
        <div className="panel-grid">
          <div>
            <label>Database</label>
            <select value={selectedConnection} onChange={(event) => setSelectedConnection(event.target.value)}>
              {connections.map((conn) => (
                <option key={conn.id} value={conn.id}>
                  {conn.name}
                </option>
              ))}
            </select>
          </div>
          <div className="panel-actions">
            <button className="secondary-button" onClick={refreshConnections}>
              Refresh Connections
            </button>
          </div>
        </div>
      </section>

      <section className="panel">
        <div className="section-header">
          <div>
            <p className="eyebrow">Search Table</p>
            <h2>Search database tables</h2>
          </div>
          {searchLoading && <div className="status-chip">Searching tables...</div>}
        </div>
        <input
          type="text"
          value={searchTerm}
          onChange={(event) => setSearchTerm(event.target.value)}
          placeholder="🔍 Enter table name"
        />
        <div className="search-results">
          {searchResults.length === 0 && searchTerm && !searchLoading && <p className="muted">No matching tables found.</p>}
          {searchResults.map((table) => (
            <button
              key={table}
              className={`table-item ${selectedTable === table ? "selected" : ""}`}
              onClick={() => handleSelectTable(table)}
            >
              {table}
            </button>
          ))}
        </div>
        <div className="form-row">
          <div>
            <label>Selected Table</label>
            <input type="text" value={selectedTable} readOnly />
          </div>
          <button className="primary-button" onClick={loadTableSchema} disabled={!selectedTable || schemaLoading}>
            {schemaLoading ? "Loading schema..." : "Submit"}
          </button>
        </div>
      </section>

      <section className="panel">
        <div className="section-header">
          <div>
            <p className="eyebrow">Bulk Table Documentation</p>
            <h2>Upload a file containing table names</h2>
          </div>
          {uploadStatus && <div className="status-chip">{uploadStatus}</div>}
        </div>
        <p className="note">Supported formats: CSV, XLSX, XLS. The first column should contain table names.</p>
        <div className="file-upload-row">
          <input type="file" accept=".csv,.xlsx,.xls" onChange={(event) => setUploadFile(event.target.files?.[0] ?? null)} />
          <button className="primary-button" onClick={handleUpload} disabled={!uploadFile}>
            Upload &amp; Process
          </button>
        </div>
      </section>

      {uploadSummary && (
        <section className="panel summary-panel">
          <h2>Bulk Documentation Completed</h2>
          <div className="summary-grid">
            <div>
              <strong>Database</strong>
              <p>{selectedConnectionMeta?.name}</p>
            </div>
            <div>
              <strong>Uploaded</strong>
              <p>{uploadSummary.total} tables</p>
            </div>
            <div>
              <strong>Processed</strong>
              <p>{uploadSummary.processed}</p>
            </div>
            <div>
              <strong>Not Found</strong>
              <p>{uploadSummary.not_found}</p>
            </div>
          </div>
          <div className="table-list">
            <div>
              <h3>Processed Tables</h3>
              {uploadSummary.found.map((table) => (
                <p key={table}>✓ {table}</p>
              ))}
            </div>
            <div>
              <h3>Not Found</h3>
              {uploadSummary.not_found_list.map((table) => (
                <p key={table}>✕ {table}</p>
              ))}
            </div>
          </div>
          <div className="download-row">
            {downloadLink && (
              <a className="secondary-button" href={downloadLink} target="_blank" rel="noreferrer">
                Download Complete Documentation
              </a>
            )}
            <button className="secondary-button" onClick={handlePublishGoogleSheet}>
              Generate Google Sheet
            </button>
          </div>
          {googleSheetStatus && <p className="muted">{googleSheetStatus}</p>}
        </section>
      )}

      {schema.length > 0 && (
        <section className="panel schema-panel">
          <div className="section-header">
            <div>
              <p className="eyebrow">Table Structure</p>
              <h2>{tableInfo.table_name}</h2>
              <p>
                Database: {tableInfo.connection_name} • Schema: {tableInfo.schema} • Columns: {tableInfo.column_count}
              </p>
            </div>
            {downloadLink && (
              <a className="secondary-button" href={downloadLink} target="_blank" rel="noreferrer">
                Download Table Documentation
              </a>
            )}
          </div>
          <div className="table-grid">
            <div className="table-row header-row">
              <div>Column Name</div>
              <div>Data Type</div>
              <div>Nullable</div>
              <div>PK</div>
              <div>FK</div>
              <div>Referenced Table</div>
              <div>Referenced Column</div>
              <div>Default</div>
              <div>Description</div>
            </div>
            {schema.map((column) => (
              <div className="table-row" key={column.column_name}>
                <div>{column.column_name}</div>
                <div>{column.data_type}</div>
                <div>{column.is_nullable ? "YES" : "NO"}</div>
                <div>{column.is_primary ? "YES" : ""}</div>
                <div>{column.foreign_key?.constraint_name || ""}</div>
                <div>{column.foreign_key?.referenced_table || ""}</div>
                <div>{column.foreign_key?.referenced_column || ""}</div>
                <div>{column.column_default || ""}</div>
                <div>{column.column_comment || ""}</div>
              </div>
            ))}
          </div>
        </section>
      )}

      {errorMessage && <div className="error-banner">{errorMessage}</div>}

      {showAddDatabase && (
        <div className="modal-overlay" onClick={() => setShowAddDatabase(false)}>
          <div className="modal" onClick={(event) => event.stopPropagation()}>
            <h2>Add Database</h2>
            <div className="form-grid">
              <label>
                Database Name
                <input
                  value={connectionForm.name}
                  onChange={(event) => setConnectionForm({ ...connectionForm, name: event.target.value })}
                />
              </label>
              <label>
                Host
                <input
                  value={connectionForm.host}
                  onChange={(event) => setConnectionForm({ ...connectionForm, host: event.target.value })}
                />
              </label>
              <label>
                Port
                <input
                  type="number"
                  value={connectionForm.port}
                  onChange={(event) => setConnectionForm({ ...connectionForm, port: Number(event.target.value) })}
                />
              </label>
              <label>
                Database
                <input
                  value={connectionForm.database}
                  onChange={(event) => setConnectionForm({ ...connectionForm, database: event.target.value })}
                />
              </label>
              <label>
                Username
                <input
                  value={connectionForm.username}
                  onChange={(event) => setConnectionForm({ ...connectionForm, username: event.target.value })}
                />
              </label>
              <label>
                Password
                <input
                  type="password"
                  value={connectionForm.password}
                  onChange={(event) => setConnectionForm({ ...connectionForm, password: event.target.value })}
                />
              </label>
              <label>
                Schema
                <input
                  value={connectionForm.schema}
                  onChange={(event) => setConnectionForm({ ...connectionForm, schema: event.target.value })}
                />
              </label>
            </div>
            <div className="modal-actions">
              <button className="secondary-button" onClick={handleTestConnection}>
                Test Connection
              </button>
              <button className="primary-button" onClick={handleSaveConnection}>
                Save Database
              </button>
            </div>
            {testStatus && <p className="muted">{testStatus}</p>}
          </div>
        </div>
      )}
    </div>
  );
}

export default App;
