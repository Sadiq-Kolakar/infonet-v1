import { Component, useEffect, useRef, useState } from "react";
import type { ErrorInfo, ReactNode } from "react";
import {
  BrowserRouter,
  NavLink,
  Route,
  Routes,
  useNavigate,
  useParams,
} from "react-router-dom";
import type { Core } from "cytoscape";
import {
  Activity,
  ArrowDown,
  ArrowLeft,
  ArrowRight,
  BookOpen,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  CircleHelp,
  Database,
  ExternalLink,
  FlaskConical,
  GitBranch,
  GraduationCap,
  Info,
  LayoutDashboard,
  Menu,
  Network,
  RefreshCw,
  Search,
  ShieldAlert,
  Users,
  X,
} from "lucide-react";
import { api, getErrorMessage } from "./api/client";
import type { DataQualityItem, EntitySummary, PageResult } from "./api/types";
import "./index.css";

type Resource<T> = {
  data: T | null;
  error: unknown;
  loading: boolean;
  retry: () => void;
};
function useResource<T>(
  loader: (signal: AbortSignal) => Promise<T>,
  key: string,
  enabled = true,
): Resource<T> {
  const [revision, setRevision] = useState(0);
  const requestKey = `${key}:${revision}`;
  const [snapshot, setSnapshot] = useState<{
    key: string;
    data: T | null;
    error: unknown;
  }>({ key: "", data: null, error: null });
  const loaderRef = useRef(loader);
  useEffect(() => {
    loaderRef.current = loader;
  }, [loader]);
  useEffect(() => {
    if (!enabled) return;
    const controller = new AbortController();
    loaderRef
      .current(controller.signal)
      .then((value) => {
        if (!controller.signal.aborted)
          setSnapshot({ key: requestKey, data: value, error: null });
      })
      .catch((reason: unknown) => {
        if (!controller.signal.aborted)
          setSnapshot({ key: requestKey, data: null, error: reason });
      });
    return () => controller.abort();
  }, [requestKey, enabled]);
  const current = snapshot.key === requestKey;
  return {
    data: enabled && current ? snapshot.data : null,
    error: enabled && current ? snapshot.error : null,
    loading: enabled && !current,
    retry: () => setRevision((value) => value + 1),
  };
}
function useDebounced(value: string, delay = 250): string {
  const [result, setResult] = useState(value);
  useEffect(() => {
    const timer = window.setTimeout(() => setResult(value), delay);
    return () => window.clearTimeout(timer);
  }, [value, delay]);
  return result;
}

const navItems = [
  { to: "/", label: "Overview", icon: LayoutDashboard, end: true },
  { to: "/people", label: "People", icon: Users },
  { to: "/laboratories", label: "Laboratories", icon: FlaskConical },
  { to: "/programs", label: "Programs", icon: GraduationCap },
  { to: "/graph", label: "Knowledge graph", icon: Network },
  { to: "/data-quality", label: "Data quality", icon: ShieldAlert },
  { to: "/about", label: "About", icon: Info },
];

function AppShell() {
  const [mobileOpen, setMobileOpen] = useState(false);
  const health = useResource((signal) => api.health(signal), "health");
  const healthLabel =
    health.data?.database === "up" && health.data.data_loaded
      ? "Database connected"
      : health.data?.database === "up"
        ? "Data not loaded"
        : health.data
          ? "Database unavailable"
          : health.error
            ? "API unavailable"
            : "Checking connection";
  return (
    <div className="app-shell">
      {mobileOpen && (
        <button
          className="scrim"
          aria-label="Close navigation"
          onClick={() => setMobileOpen(false)}
        />
      )}
      <aside className={`sidebar ${mobileOpen ? "sidebar-open" : ""}`}>
        <div className="brand">
          <div className="brand-mark">
            <Network size={19} strokeWidth={2.2} />
          </div>
          <div>
            <strong>infonet</strong>
            <span>Knowledge portal</span>
          </div>
          <button
            className="icon-button mobile-close"
            aria-label="Close navigation"
            onClick={() => setMobileOpen(false)}
          >
            <X size={18} />
          </button>
        </div>
        <div className="workspace-tag">
          <span className="live-dot" /> SIT{" "}
          <span className="tag-divider">/</span> CSE
        </div>
        <div className="nav-caption">EXPLORE</div>
        <nav aria-label="Main navigation">
          {navItems.map(({ to, label, icon: Icon, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              onClick={() => setMobileOpen(false)}
              className={({ isActive }) =>
                `nav-link ${isActive ? "active" : ""}`
              }
            >
              <Icon size={17} strokeWidth={1.8} />
              <span>{label}</span>
              {label === "Data quality" && <span className="nav-dot" />}
            </NavLink>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <div className="connection-card">
            <div className="connection-top">
              <span
                className={`connection-dot ${health.data?.database === "up" && health.data.data_loaded ? "is-up" : ""}`}
              />
              <span>{healthLabel}</span>
            </div>
            <span className="connection-sub">Read-only knowledge graph</span>
          </div>
          <div className="sidebar-foot">
            Siddaganga Institute of Technology{" "}
            <span>Local demonstration · English</span>
          </div>
        </div>
      </aside>
      <main className="main-area">
        <header className="topbar">
          <button
            className="icon-button menu-toggle"
            aria-label="Open navigation"
            onClick={() => setMobileOpen(true)}
          >
            <Menu size={20} />
          </button>
          <div className="breadcrumbs">
            <span>INFONET</span>
            <span className="crumb-slash">/</span>
            <span className="crumb-current">CSE Knowledge Graph</span>
          </div>
          <div className="topbar-right">
            <span className="read-only">
              <Database size={14} /> Read only
            </span>
          </div>
        </header>
        <div className="page-wrap">
          <Routes>
            <Route path="/" element={<DashboardPage />} />
            <Route path="/people" element={<DirectoryPage kind="people" />} />
            <Route
              path="/laboratories"
              element={<DirectoryPage kind="labs" />}
            />
            <Route
              path="/programs"
              element={<DirectoryPage kind="programs" />}
            />
            <Route path="/entities/:id" element={<EntityPage />} />
            <Route path="/graph" element={<GraphPage />} />
            <Route path="/data-quality" element={<DataQualityPage />} />
            <Route path="/about" element={<AboutPage />} />
            <Route path="*" element={<NotFound />} />
          </Routes>
        </div>
        <footer className="page-footer">
          <span>
            INFONET <b>·</b> SIT Computer Science & Engineering
          </span>
          <span>Source data may require review</span>
        </footer>
      </main>
    </div>
  );
}

function PageHeading({
  eyebrow,
  title,
  description,
  action,
}: {
  eyebrow: string;
  title: string;
  description: string;
  action?: ReactNode;
}) {
  return (
    <div className="page-heading">
      <div>
        <div className="eyebrow">{eyebrow}</div>
        <h1>{title}</h1>
        <p>{description}</p>
      </div>
      {action}
    </div>
  );
}
function LoadingState({ label = "Loading live data" }: { label?: string }) {
  return (
    <div className="loading-card" role="status">
      <span className="spinner" />
      <span>{label}</span>
    </div>
  );
}
function ErrorState({ error, retry }: { error: unknown; retry: () => void }) {
  return (
    <div className="state-card error-state">
      <div className="state-icon danger">
        <Activity size={20} />
      </div>
      <div>
        <h3>We couldn’t load this data</h3>
        <p>{getErrorMessage(error)}</p>
        <button className="button button-outline button-small" onClick={retry}>
          <RefreshCw size={14} /> Try again
        </button>
      </div>
    </div>
  );
}
function EmptyState({ title, detail }: { title: string; detail: string }) {
  return (
    <div className="empty-state">
      <div className="state-icon">
        <Search size={19} />
      </div>
      <h3>{title}</h3>
      <p>{detail}</p>
    </div>
  );
}
function StatusBadge({ code, label }: { code?: string; label?: string }) {
  const text =
    label ??
    (code === "inferred_link"
      ? "Inferred · needs review"
      : code === "user_confirmed_assertion"
        ? "User-confirmed · not independently verified"
        : code === "unverified_claim"
          ? "Unverified source claim"
          : code === "unresolved_conflict"
            ? "Conflict unresolved"
            : code === "not_recorded"
              ? "Not recorded"
              : "Source-stated · needs review");
  const kind =
    code === "user_confirmed_assertion"
      ? "confirmed"
      : code === "unresolved_conflict"
        ? "conflict"
        : code === "inferred_link" || code === "unverified_claim"
          ? "review"
          : "neutral";
  return (
    <span className={`status-badge badge-${kind}`}>
      <span className="badge-indicator" />
      {text}
    </span>
  );
}
function MetricCard({
  label,
  value,
  icon: Icon,
  note,
  to,
}: {
  label: string;
  value: number | string;
  icon: typeof Users;
  note: string;
  to?: string;
}) {
  const body = (
    <>
      <div className="metric-top">
        <span className="metric-label">{label}</span>
        <span className="metric-icon">
          <Icon size={17} />
        </span>
      </div>
      <div className="metric-value">{value}</div>
      <div className="metric-note">{note}</div>
    </>
  );
  return to ? (
    <NavLink to={to} className="metric-card metric-link">
      {body}
      <ArrowRight className="metric-arrow" size={15} />
    </NavLink>
  ) : (
    <div className="metric-card">{body}</div>
  );
}

function DashboardPage() {
  const { data, error, loading, retry } = useResource(async (signal) => {
    const [summary, health] = await Promise.all([
      api.summary(signal),
      api.health(signal),
    ]);
    return { summary, health };
  }, "dashboard");
  const quality = useResource(
    (signal) => api.dataQuality(signal),
    "dashboard-quality",
  );
  const conflictCount = quality.data?.items.filter(
    (item) => item.kind === "conflict",
  ).length;
  const unverifiedClaimCount = quality.data?.items.filter(
    (item) => item.kind === "source_claim",
  ).length;
  return (
    <>
      <PageHeading
        eyebrow="DEPARTMENT OVERVIEW"
        title="A connected view of CSE."
        description="Explore people, programmes, laboratories and the relationships between them."
        action={
          data?.health.database === "up" && data.health.data_loaded ? (
            <span className="dataset-chip">
              <span className="live-dot" /> Live dataset
            </span>
          ) : undefined
        }
      />
      {loading && (
        <LoadingState label="Connecting to the INFONET knowledge graph" />
      )}
      {error && <ErrorState error={error} retry={retry} />}
      {data && (
        <>
          {data.health.database !== "up" && (
            <div className="notice notice-danger">
              <Database size={17} />
              <div>
                <strong>Database unavailable</strong>
                <span>
                  The API is online, but live knowledge graph data cannot be
                  loaded right now.
                </span>
              </div>
            </div>
          )}
          {data.health.database === "up" && !data.health.data_loaded && (
            <div className="notice notice-warn">
              <Database size={17} />
              <div>
                <strong>No dataset loaded</strong>
                <span>
                  The database is reachable, but it does not currently contain
                  INFONET data.
                </span>
              </div>
            </div>
          )}
          <div className="overview-banner">
            <div className="banner-icon">
              <BookOpen size={20} />
            </div>
            <div className="banner-copy">
              <span className="banner-kicker">
                SIDDAGANGA INSTITUTE OF TECHNOLOGY <i>·</i> TUMAKURU
              </span>
              <h2>
                {data.summary.department.name ??
                  "Department information not recorded"}
              </h2>
              <p>
                {data.summary.department.description ??
                  "A department description has not been recorded in the current dataset."}
              </p>
              <a
                href={data.summary.department.source_url ?? undefined}
                target="_blank"
                rel="noreferrer"
                className={`source-link ${data.summary.department.source_url ? "" : "disabled-link"}`}
              >
                View source page <ExternalLink size={13} />
              </a>
            </div>
            <div className="banner-index">
              <span>DEPARTMENT</span>
              <strong>
                {String(data.summary.department_count).padStart(2, "0")}
              </strong>
              <small>in current dataset</small>
            </div>
          </div>
          <div className="section-row">
            <div>
              <div className="section-eyebrow">AT A GLANCE</div>
              <h2 className="section-title">Department snapshot</h2>
            </div>
            <span className="computed-note">
              Counts computed from loaded graph data
            </span>
          </div>
          <div className="metric-grid">
            <MetricCard
              label="Faculty"
              value={data.summary.counts.faculty}
              note="Academic staff"
              icon={Users}
              to="/people"
            />
            <MetricCard
              label="Support staff"
              value={data.summary.counts.support_staff}
              note="People directory"
              icon={Users}
              to="/people"
            />
            <MetricCard
              label="Laboratories"
              value={data.summary.counts.laboratories}
              note="Facilities listed"
              icon={FlaskConical}
              to="/laboratories"
            />
            <MetricCard
              label="Program records"
              value={data.summary.counts.programs}
              note="Includes unresolved conflict"
              icon={GraduationCap}
              to="/programs"
            />
          </div>
          <div className="lower-grid">
            <section className="panel graph-teaser">
              <div className="panel-heading">
                <div>
                  <div className="section-eyebrow">RELATIONSHIPS</div>
                  <h2>Explore the graph</h2>
                </div>
                <NavLink className="text-link" to="/graph">
                  Open graph <ArrowRight size={14} />
                </NavLink>
              </div>
              <div className="graph-stats">
                <div className="graph-visual">
                  <span className="graph-node node-a" />
                  <span className="graph-node node-b" />
                  <span className="graph-node node-c" />
                  <span className="graph-line line-a" />
                  <span className="graph-line line-b" />
                </div>
                <div>
                  <div className="big-stat">
                    {data.summary.counts.relationships}
                    <span> relationships</span>
                  </div>
                  <p>
                    {data.summary.data_status.relationships_inferred} inferred
                    links need review
                  </p>
                </div>
              </div>
              <div className="relation-legend">
                <span>
                  <i className="legend-dot inferred-dot" /> Inferred · needs
                  review
                </span>
                <span>
                  <i className="legend-dot confirmed-dot" /> User-confirmed ·
                  not independently verified
                </span>
              </div>
            </section>
            <section className="panel quality-panel">
              <div className="panel-heading">
                <div>
                  <div className="section-eyebrow">DATA INTEGRITY</div>
                  <h2>Review & uncertainty</h2>
                </div>
                <NavLink
                  className="quiet-icon-link"
                  to="/data-quality"
                  aria-label="Open data quality"
                >
                  <ArrowRight size={16} />
                </NavLink>
              </div>
              <div className="quality-summary">
                <div className="quality-number">
                  {quality.data?.total ?? "—"}
                </div>
                <div>
                  <strong>Open data-quality items</strong>
                  <span>
                    Source claims and records need careful interpretation.
                  </span>
                </div>
              </div>
              <div className="quality-line">
                <span>Unresolved conflicts</span>
                <strong>{conflictCount ?? "—"}</strong>
              </div>
              <div className="quality-line">
                <span>Unverified source claims</span>
                <strong>{unverifiedClaimCount ?? "—"}</strong>
              </div>
              <div className="quality-line">
                <span>Inferred relationships</span>
                <strong>
                  {data.summary.data_status.relationships_inferred}
                </strong>
              </div>
              <NavLink to="/data-quality" className="quality-footer">
                Review data quality <ArrowRight size={14} />
              </NavLink>
            </section>
          </div>
          <div className="integrity-note">
            <ShieldAlert size={16} />
            <span>
              Source-derived data may be incomplete or require review. INFONET
              does not independently verify these records.
            </span>
            <NavLink to="/about">About data status</NavLink>
          </div>
        </>
      )}
    </>
  );
}

type DirectoryKind = "people" | "labs" | "programs";
const directoryConfig: Record<
  DirectoryKind,
  { title: string; eyebrow: string; description: string; icon: typeof Users }
> = {
  people: {
    title: "People",
    eyebrow: "DIRECTORY",
    description: "Find faculty and support staff in the CSE department.",
    icon: Users,
  },
  labs: {
    title: "Laboratories",
    eyebrow: "INFRASTRUCTURE",
    description: "Browse the laboratories listed for the CSE department.",
    icon: FlaskConical,
  },
  programs: {
    title: "Academic programs",
    eyebrow: "ACADEMICS",
    description:
      "Explore program records while keeping unresolved source conflicts visible.",
    icon: GraduationCap,
  },
};
function DirectoryPage({ kind }: { kind: DirectoryKind }) {
  const searchParams = new URLSearchParams(window.location.search);
  const [input, setInput] = useState(searchParams.get("q") ?? "");
  const [category, setCategory] = useState(searchParams.get("category") ?? "");
  const [roleTitle, setRoleTitle] = useState("");
  const [level, setLevel] = useState("");
  const [page, setPage] = useState(0);
  const query = useDebounced(input.trim());
  const pageSize = 12;
  const filterFacets = useResource(
    (signal) => api.people({ limit: 1 }, signal),
    "people-filter-facets",
    kind === "people",
  );
  const loader = (signal: AbortSignal) =>
    kind === "people"
      ? api.people(
          {
            q: query,
            category: category || undefined,
            role_title: roleTitle || undefined,
            limit: pageSize,
            offset: page * pageSize,
          },
          signal,
        )
      : kind === "labs"
        ? api.laboratories(
            { q: query, limit: pageSize, offset: page * pageSize },
            signal,
          )
        : api.programs(
            {
              q: query,
              level: level || undefined,
              limit: pageSize,
              offset: page * pageSize,
            },
            signal,
          );
  const { data, error, loading, retry } = useResource<
    PageResult<EntitySummary>
  >(loader, `${kind}:${query}:${category}:${roleTitle}:${level}:${page}`);
  const config = directoryConfig[kind];
  const Icon = config.icon;
  return (
    <>
      <PageHeading
        eyebrow={config.eyebrow}
        title={config.title}
        description={config.description}
      />
      {kind === "programs" &&
        data?.items.some((item) =>
          Boolean(item.conflict || item.attributes.conflict_group),
        ) && (
          <div className="notice notice-warn">
            <ShieldAlert size={17} />
            <div>
              <strong>Conflicting records are preserved</strong>
              <span>
                Both evening-program entries remain listed. The available source
                data does not resolve their level or duration disagreement.
              </span>
            </div>
          </div>
        )}
      <section className="panel directory-panel">
        <div className="directory-toolbar">
          <label className="search-field">
            <Search size={17} />
            <span className="sr-only">Search {config.title.toLowerCase()}</span>
            <input
              value={input}
              onChange={(event) => {
                setInput(event.target.value);
                setPage(0);
              }}
              placeholder={`Search ${config.title.toLowerCase()}…`}
            />
          </label>
          {kind === "people" && (
            <>
              <label className="select-field">
                <span className="sr-only">Filter by category</span>
                <select
                  value={category}
                  onChange={(event) => {
                    setCategory(event.target.value);
                    setPage(0);
                  }}
                >
                  <option value="">All categories</option>
                  {Object.keys(
                    filterFacets.data?.facets.person_category ?? {},
                  ).map((value) => (
                    <option value={value} key={value}>
                      {value}
                    </option>
                  ))}
                </select>
                <ChevronRight size={14} />
              </label>
              <label className="select-field">
                <span className="sr-only">Filter by role title</span>
                <select
                  value={roleTitle}
                  onChange={(event) => {
                    setRoleTitle(event.target.value);
                    setPage(0);
                  }}
                >
                  <option value="">All role titles</option>
                  {[
                    ...new Set([
                      ...(roleTitle ? [roleTitle] : []),
                      ...Object.keys(
                        filterFacets.data?.facets.role_title ?? {},
                      ),
                    ]),
                  ].map((value) => (
                    <option value={value} key={value}>
                      {value}
                    </option>
                  ))}
                </select>
                <ChevronRight size={14} />
              </label>
            </>
          )}
          {kind === "programs" && (
            <label className="select-field">
              <span className="sr-only">Filter by level</span>
              <select
                value={level}
                onChange={(event) => {
                  setLevel(event.target.value);
                  setPage(0);
                }}
              >
                <option value="">All levels</option>
                <option value="UG">Undergraduate (UG)</option>
                <option value="PG">Postgraduate (PG)</option>
                <option value="Research">Research</option>
              </select>
              <ChevronRight size={14} />
            </label>
          )}
        </div>
        <div className="results-caption">
          {data ? (
            <>
              <strong>{data.total}</strong> records <span>·</span>{" "}
              {query ? <>matching “{query}”</> : "from current dataset"}
            </>
          ) : (
            "Search the live INFONET dataset"
          )}
        </div>
        {loading && (
          <div className="list-skeleton" aria-label="Loading results">
            {Array.from({ length: 5 }, (_, index) => (
              <div className="skeleton-row" key={index}>
                <span />
                <span />
                <span />
              </div>
            ))}
          </div>
        )}
        {Boolean(error) && !loading && (
          <ErrorState error={error} retry={retry} />
        )}
        {data && !loading && data.items.length === 0 && (
          <EmptyState
            title="No matching records"
            detail="Try a different search or clear the selected filters."
          />
        )}
        {data && !loading && data.items.length > 0 && (
          <div className="record-list">
            {data.items.map((item) => (
              <RecordRow key={item.id} item={item} icon={Icon} kind={kind} />
            ))}
          </div>
        )}
        {data && data.total > pageSize && (
          <div className="pagination">
            <span>
              Showing {page * pageSize + 1}–
              {Math.min((page + 1) * pageSize, data.total)} of {data.total}
            </span>
            <div>
              <button
                aria-label="Previous page"
                className="icon-button page-button"
                disabled={page === 0}
                onClick={() => setPage((value) => Math.max(0, value - 1))}
              >
                <ChevronLeft size={17} />
              </button>
              <span className="page-number">{page + 1}</span>
              <button
                aria-label="Next page"
                className="icon-button page-button"
                disabled={(page + 1) * pageSize >= data.total}
                onClick={() => setPage((value) => value + 1)}
              >
                <ChevronRight size={17} />
              </button>
            </div>
          </div>
        )}
      </section>
      <div className="inline-footnote">
        <Info size={14} /> Information is shown as stored. Missing values are
        not inferred.
      </div>
    </>
  );
}
function RecordRow({
  item,
  icon: Icon,
  kind,
}: {
  item: EntitySummary;
  icon: typeof Users;
  kind: DirectoryKind;
}) {
  const attr = item.attributes;
  const conflict = Boolean(item.conflict || attr.conflict_group);
  return (
    <NavLink
      to={`/entities/${encodeURIComponent(item.id)}`}
      className="record-row"
    >
      <div className={`record-icon record-${kind}`}>
        <Icon size={18} />
      </div>
      <div className="record-main">
        <div className="record-title-line">
          <strong>{item.name}</strong>
          {conflict && (
            <StatusBadge
              code="unresolved_conflict"
              label="Conflict · both records retained"
            />
          )}
        </div>
        <div className="record-subtitle">
          {kind === "people"
            ? String(
                attr.role_title ?? attr.person_category ?? "Role not recorded",
              )
            : kind === "programs"
              ? [attr.level, attr.duration].filter(Boolean).join(" · ") ||
                "Program details not recorded"
              : "Name listed · description not recorded"}
        </div>
      </div>
      <div className="record-status">
        <StatusBadge code={item.status.display_codes[0]} />
        <ArrowRight size={15} />
      </div>
    </NavLink>
  );
}

function EntityPage() {
  const { id = "" } = useParams();
  const navigate = useNavigate();
  const { data, error, loading, retry } = useResource(
    (signal) => api.entity(id, signal),
    `entity:${id}`,
  );
  if (loading)
    return (
      <>
        <button className="back-link" onClick={() => navigate(-1)}>
          <ArrowLeft size={14} /> Back
        </button>
        <LoadingState label="Loading entity details" />
      </>
    );
  if (error)
    return (
      <>
        <button className="back-link" onClick={() => navigate(-1)}>
          <ArrowLeft size={14} /> Back
        </button>
        <ErrorState error={error} retry={retry} />
      </>
    );
  if (!data) return null;
  const e = data.entity;
  const attrEntries = Object.entries(e.attributes).filter(
    ([, value]) => value !== null && value !== "",
  );
  const relatedGroups = Object.entries(data.related).flatMap(
    ([group, entities]) => entities.map((item) => ({ group, item })),
  );
  const missing = [
    ...new Set([...(e.missing_fields ?? []), ...(e.absent_attributes ?? [])]),
  ];
  return (
    <>
      <button className="back-link" onClick={() => navigate(-1)}>
        <ArrowLeft size={14} /> Back to previous view
      </button>
      <div className="detail-header">
        <div className={`record-icon record-${e.type.toLowerCase()}`}>
          <EntityIcon type={e.type} />
        </div>
        <div>
          <div className="eyebrow">{e.type.toUpperCase()} RECORD</div>
          <h1>{e.name}</h1>
          <div className="detail-badges">
            {data.status.display_codes.map((code) => (
              <StatusBadge key={code} code={code} />
            ))}
          </div>
        </div>
      </div>
      {e.id === "DERIVED-PERSON-3e943445fa58" &&
        relatedGroups.some(
          ({ item }) => (item.rel_type ?? item.type_name) === "IS_HOD_OF",
        ) && (
          <div className="notice notice-blue">
            <CheckCircle2 size={17} />
            <div>
              <strong>Current HOD · user-confirmed project assertion</strong>
              <span>
                This relationship was confirmed in project data on 26 Oct 2026.
                It has not been independently verified against an official
                institutional source.
              </span>
            </div>
          </div>
        )}
      {e.type === "Program" &&
        (e.attributes.conflict_group ||
          data.observations.some(
            (o) => o.observation_type === "ProgramConflict",
          )) && (
          <div className="notice notice-warn">
            <ShieldAlert size={17} />
            <div>
              <strong>Unresolved source conflict</strong>
              <span>
                This program is one of two preserved evening-program records.
                Neither entry is treated as authoritative.
              </span>
            </div>
          </div>
        )}
      <div className="detail-grid">
        <section className="panel detail-panel">
          <div className="panel-heading">
            <div>
              <div className="section-eyebrow">RECORD</div>
              <h2>Available information</h2>
            </div>
          </div>
          {attrEntries.length ? (
            <dl className="attribute-list">
              {attrEntries.map(([key, value]) => (
                <div key={key}>
                  <dt>{humanize(key)}</dt>
                  <dd>
                    {key.endsWith("_url") ? (
                      <a
                        href={String(value)}
                        target="_blank"
                        rel="noreferrer"
                        className="source-link"
                      >
                        Open stored link <ExternalLink size={12} />
                      </a>
                    ) : (
                      String(value)
                    )}
                  </dd>
                </div>
              ))}
            </dl>
          ) : (
            <EmptyState
              title="No attributes recorded"
              detail="The current API response does not include additional fields for this entity."
            />
          )}
          {missing.length > 0 && (
            <div className="missing-note">
              <Info size={14} />
              <span>Not recorded: {missing.map(humanize).join(", ")}</span>
            </div>
          )}
        </section>
        <section className="panel provenance-panel">
          <div className="panel-heading">
            <div>
              <div className="section-eyebrow">EVIDENCE</div>
              <h2>Provenance</h2>
            </div>
            <ShieldAlert size={17} />
          </div>
          <p className="panel-intro">
            Source and review information as returned by the API.
          </p>
          <dl className="attribute-list compact-list">
            {Object.entries(data.provenance)
              .filter(([, value]) => value !== null && value !== undefined)
              .map(([key, value]) => (
                <div key={key}>
                  <dt>{humanize(key)}</dt>
                  <dd>
                    {key === "source_url" ? (
                      <a
                        href={String(value)}
                        target="_blank"
                        rel="noreferrer"
                        className="source-link"
                      >
                        Open source <ExternalLink size={12} />
                      </a>
                    ) : (
                      String(value)
                    )}
                  </dd>
                </div>
              ))}
          </dl>
          {Object.values(data.provenance).every((value) => value == null) && (
            <p className="muted-copy">
              No provenance values were supplied for this record.
            </p>
          )}
        </section>
      </div>
      {(relatedGroups.length > 0 ||
        data.observations.length > 0 ||
        data.notes.length > 0) && (
        <section className="panel related-panel">
          <div className="panel-heading">
            <div>
              <div className="section-eyebrow">CONTEXT</div>
              <h2>Connections & notes</h2>
            </div>
          </div>
          {relatedGroups.length > 0 && (
            <div className="related-list">
              {relatedGroups.map(({ group, item }, index) => {
                const entityId = item.entity_id ?? item.id;
                const relType =
                  item.rel_type ?? item.type_name ?? group.toUpperCase();
                return (
                  <div className="related-item" key={`${entityId}-${index}`}>
                    <GitBranch size={16} />
                    <div className="related-copy">
                      <strong>
                        {humanize(relType)} <span>{item.direction}</span>
                      </strong>
                      {entityId ? (
                        <NavLink
                          to={`/entities/${encodeURIComponent(entityId)}`}
                        >
                          {item.entity_name ?? item.name ?? entityId}{" "}
                          <ArrowRight size={13} />
                        </NavLink>
                      ) : (
                        <span>
                          {item.entity_name ??
                            item.name ??
                            "Linked entity name not provided"}
                        </span>
                      )}
                      <StatusBadge code={item.status_code} />
                      {item.source_url && (
                        <a
                          href={item.source_url}
                          target="_blank"
                          rel="noreferrer"
                          className="source-link"
                        >
                          Open relationship source <ExternalLink size={12} />
                        </a>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
          {data.observations.map((obs) => (
            <div className="observation-card" key={obs.id}>
              <StatusBadge code={obs.status_code} />
              <strong>{humanize(obs.observation_type)}</strong>
              <p>
                {obs.source_evidence ??
                  obs.program_name ??
                  "Source observation returned by the API."}
              </p>
              {obs.members?.map((member) => (
                <div className="conflict-member" key={member.id}>
                  <NavLink to={`/entities/${encodeURIComponent(member.id)}`}>
                    Open preserved record <ArrowRight size={12} />
                  </NavLink>
                  <span>
                    {[
                      member.level,
                      member.intake_count && `intake ${member.intake_count}`,
                      member.duration,
                    ]
                      .filter(Boolean)
                      .join(" · ")}
                  </span>
                </div>
              ))}
            </div>
          ))}
          {data.notes.map((note) => (
            <div className="project-note" key={note.id}>
              <span className="note-label">
                PROJECT NOTE · {note.kind.replaceAll("_", " ")}
              </span>
              <p>{note.text}</p>
              {note.source_refs.length > 0 && (
                <small>References: {note.source_refs.join(" · ")}</small>
              )}
            </div>
          ))}
        </section>
      )}
    </>
  );
}

function GraphPage() {
  const { data, error, loading, retry } = useResource(
    (signal) => api.graph(signal),
    "graph",
  );
  const [selection, setSelection] = useState<{
    kind: "node" | "edge";
    id: string;
    label: string;
    type: string;
    status: string;
    source?: string | null;
    verified?: boolean;
  } | null>(null);
  const [hiddenTypes, setHiddenTypes] = useState<string[]>([]);
  const [instance, setInstance] = useState<Core | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!containerRef.current || !data) return;
    let disposed = false;
    let cy: Core | null = null;
    void import("cytoscape").then(({ default: cytoscape }) => {
      if (disposed || !containerRef.current) return;
      cy = cytoscape({
        container: containerRef.current,
        elements: [...data.nodes, ...data.edges].map((element) => ({
          group:
            "data" in element && "source" in element.data
              ? ("edges" as const)
              : ("nodes" as const),
          data: element.data,
        })),
        layout: {
          name: "cose",
          animate: false,
          randomize: false,
          fit: true,
          padding: 45,
          nodeRepulsion: () => 7000,
          idealEdgeLength: () => 90,
        },
        minZoom: 0.15,
        maxZoom: 4,
        style: [
          {
            selector: "node",
            style: {
              "background-color": "#e8f0ed",
              "border-color": "#6b8e7b",
              "border-width": 1.5,
              label: "",
              color: "#33443c",
              "font-size": "9px",
              "font-family": "Inter, system-ui, sans-serif",
              "text-wrap": "ellipsis",
              "text-max-width": "105",
              width: 21,
              height: 21,
              "text-valign": "bottom",
              "text-margin-y": 7,
              "text-background-color": "#fff",
              "text-background-opacity": 0.9,
              "text-background-padding": "2",
            },
          },
          {
            selector: 'node[type = "Department"], node:selected, node:active',
            style: { label: "data(label)" },
          },
          {
            selector: 'node[type = "Department"]',
            style: {
              "background-color": "#243e35",
              "border-color": "#243e35",
              width: 42,
              height: 42,
              color: "#fff",
              "font-size": "11px",
              "font-weight": 600,
              "text-margin-y": 12,
            },
          },
          {
            selector: 'node[type = "Person"]',
            style: { "background-color": "#e2eaf4", "border-color": "#8598b2" },
          },
          {
            selector: 'node[type = "Program"]',
            style: { "background-color": "#f3ead9", "border-color": "#b99d70" },
          },
          {
            selector: 'node[type = "Laboratory"]',
            style: { "background-color": "#e2eee7", "border-color": "#6b8e7b" },
          },
          {
            selector: "edge",
            style: {
              width: 1.2,
              "line-color": "#b9c8c0",
              "target-arrow-color": "#b9c8c0",
              "target-arrow-shape": "triangle",
              "curve-style": "bezier",
              opacity: 0.72,
              label: "",
            },
          },
          {
            selector: "edge:selected, edge:active",
            style: {
              label: "data(type)",
              "font-size": "8px",
              color: "#65776c",
              "text-background-color": "#fff",
              "text-background-opacity": 0.9,
              "text-background-padding": "2",
            },
          },
          {
            selector: 'edge[status_code = "user_confirmed_assertion"]',
            style: {
              "line-color": "#b88341",
              "target-arrow-color": "#b88341",
              width: 2.2,
              "line-style": "dashed",
            },
          },
          {
            selector: "edge:selected, node:selected",
            style: {
              "overlay-color": "#658a78",
              "overlay-opacity": 0.12,
              "overlay-padding": 6,
              "border-width": 3,
            },
          },
        ],
      });
      cy.on("tap", "node", (event) => {
        cy?.$(":selected").unselect();
        event.target.select();
        const d = event.target.data();
        setSelection({
          kind: "node",
          id: d.id,
          label: d.label,
          type: d.type,
          status:
            (d.status_codes as string[] | undefined)?.[0] ?? "not_recorded",
        });
      });
      cy.on("tap", "edge", (event) => {
        cy?.$(":selected").unselect();
        event.target.select();
        const d = event.target.data();
        setSelection({
          kind: "edge",
          id: d.id,
          label: `${d.type}: ${cy?.getElementById(d.source).data("label")} → ${cy?.getElementById(d.target).data("label")}`,
          type: d.type,
          status: d.status_code,
          source: d.source_url,
          verified: d.independent_source_verified,
        });
      });
      cy.on("tap", (event) => {
        if (event.target === cy) {
          cy?.$(":selected").unselect();
          setSelection(null);
        }
      });
      setInstance(cy);
    });
    return () => {
      disposed = true;
      cy?.destroy();
      setInstance(null);
    };
  }, [data]);
  useEffect(() => {
    if (!instance) return;
    instance.edges().forEach((edge) => {
      edge.style(
        "display",
        hiddenTypes.includes(String(edge.data("type"))) ? "none" : "element",
      );
    });
  }, [instance, hiddenTypes]);
  const types = data?.meta.relationship_types ?? [];
  const toggleType = (type: string) =>
    setHiddenTypes((current) =>
      current.includes(type)
        ? current.filter((item) => item !== type)
        : [...current, type],
    );
  return (
    <>
      <PageHeading
        eyebrow="CONNECTED DATA"
        title="Knowledge graph"
        description="Explore how people, programmes, laboratories and the department connect."
        action={
          data && (
            <span className="dataset-chip">
              <span className="live-dot" /> {data.meta.node_count} nodes{" "}
              <i>·</i> {data.meta.edge_count} relationships
            </span>
          )
        }
      />
      {loading && <LoadingState label="Loading graph from the live API" />}
      {error && <ErrorState error={error} retry={retry} />}
      {data && (
        <section className="graph-panel panel">
          <div className="graph-toolbar">
            <div className="filter-group">
              <span className="filter-caption">RELATIONSHIPS</span>
              {types.map((type) => (
                <button
                  key={type}
                  className={`filter-chip ${hiddenTypes.includes(type) ? "filter-off" : ""} ${type === "IS_HOD_OF" ? "filter-hod" : ""}`}
                  aria-pressed={!hiddenTypes.includes(type)}
                  onClick={() => toggleType(type)}
                >
                  <i />
                  {humanize(type)}
                </button>
              ))}
            </div>
            <div className="graph-controls">
              <button
                className="icon-button"
                aria-label="Zoom in"
                onClick={() =>
                  instance?.zoom({
                    level: instance.zoom() * 1.25,
                    renderedPosition: {
                      x: instance.width() / 2,
                      y: instance.height() / 2,
                    },
                  })
                }
              >
                ＋
              </button>
              <button
                className="icon-button"
                aria-label="Zoom out"
                onClick={() =>
                  instance?.zoom({
                    level: instance.zoom() / 1.25,
                    renderedPosition: {
                      x: instance.width() / 2,
                      y: instance.height() / 2,
                    },
                  })
                }
              >
                −
              </button>
              <button
                className="button button-outline button-small"
                onClick={() => instance?.fit(undefined, 42)}
              >
                <ArrowDown size={14} /> Fit
              </button>
            </div>
          </div>
          <div className="graph-body">
            <div className="cy-wrap">
              <div
                ref={containerRef}
                className="cy-canvas"
                role="img"
                aria-label="Interactive knowledge graph. Use the search directory or select a graph element to inspect its details."
              />
              {data.meta.node_count === 0 && (
                <EmptyState
                  title="No graph nodes"
                  detail="The live API returned an empty graph."
                />
              )}
            </div>
            <aside className="graph-side">
              <div className="graph-side-title">
                <span>INSPECT</span>
                {selection && (
                  <button
                    className="icon-button"
                    aria-label="Clear selection"
                    onClick={() => setSelection(null)}
                  >
                    <X size={15} />
                  </button>
                )}
              </div>
              {selection ? (
                <>
                  <div className="inspect-type">
                    {selection.kind} · {selection.type}
                  </div>
                  <h3>{selection.label}</h3>
                  <code className="entity-id">{selection.id}</code>
                  <StatusBadge code={selection.status} />
                  {selection.kind === "node" ? (
                    <NavLink
                      className="button button-outline inspect-button"
                      to={`/entities/${encodeURIComponent(selection.id)}`}
                    >
                      Open entity details <ArrowRight size={14} />
                    </NavLink>
                  ) : (
                    <div className="inspect-facts">
                      <div>
                        <span>Independent source verification</span>
                        <strong>{selection.verified ? "Yes" : "No"}</strong>
                      </div>
                      {selection.source && (
                        <a
                          href={selection.source}
                          target="_blank"
                          rel="noreferrer"
                          className="source-link"
                        >
                          Open stored source URL <ExternalLink size={12} />
                        </a>
                      )}
                    </div>
                  )}
                </>
              ) : (
                <div className="inspect-empty">
                  <div className="state-icon">
                    <Network size={18} />
                  </div>
                  <strong>Select a node or relationship</strong>
                  <p>
                    Choose a graph element to inspect its label, type and review
                    status.
                  </p>
                </div>
              )}
              <div className="graph-legend">
                <span className="filter-caption">STATUS KEY</span>
                <div>
                  <i className="legend-line inferred-line" /> Inferred · needs
                  review
                </div>
                <div>
                  <i className="legend-line confirmed-line" /> User-confirmed ·
                  not independently verified
                </div>
              </div>
            </aside>
          </div>
          <div className="graph-foot">
            <span>
              Drag to pan <i>·</i> Scroll to zoom <i>·</i> Select nodes for
              details
            </span>
            <span>Relationships and IDs are supplied by the API</span>
          </div>
        </section>
      )}
      {data && (
        <details className="mobile-graph-records">
          <summary>
            Browse graph entities as a list{" "}
            <span>{data.nodes.length} nodes</span>
          </summary>
          <div className="record-list">
            {data.nodes.map((node) => (
              <NavLink
                key={node.data.id}
                className="record-row"
                to={`/entities/${encodeURIComponent(node.data.id)}`}
              >
                <span className="record-icon">
                  <EntityIcon type={node.data.type} />
                </span>
                <span className="record-main">
                  <strong>{node.data.label}</strong>
                  <small>{node.data.type}</small>
                </span>
                <ArrowRight size={15} />
              </NavLink>
            ))}
          </div>
        </details>
      )}
    </>
  );
}

function DataQualityPage() {
  const { data, error, loading, retry } = useResource(
    (signal) => api.dataQuality(signal),
    "quality",
  );
  return (
    <>
      <PageHeading
        eyebrow="DATA INTEGRITY"
        title="Review the evidence."
        description="Open questions, source limitations and confidence states returned by the INFONET API."
        action={
          data && (
            <span className="dataset-chip">
              <ShieldAlert size={14} /> {data.total} open items
            </span>
          )
        }
      />
      <div className="notice notice-blue">
        <Info size={17} />
        <div>
          <strong>Transparency is part of the dataset</strong>
          <span>
            These notes describe known limitations. INFONET does not
            independently verify the source material.
          </span>
        </div>
      </div>
      {loading && <LoadingState label="Loading data-quality items" />}
      {error && <ErrorState error={error} retry={retry} />}
      {data && data.items.length === 0 && (
        <EmptyState
          title="No data-quality items returned"
          detail="The live API returned no quality items."
        />
      )}
      {data &&
        data.items.map((item) => <QualityCard item={item} key={item.id} />)}
    </>
  );
}
function QualityCard({ item }: { item: DataQualityItem }) {
  return (
    <article className="quality-card panel">
      <div className="quality-card-top">
        <span className={`severity severity-${item.severity}`}>
          {item.severity} priority
        </span>
        <span className="quality-id">{item.id}</span>
      </div>
      <h2>{item.title}</h2>
      <p>{item.explanation}</p>
      <div className="quality-meta">
        <span>{humanize(item.kind)}</span>
        <span>Origin: {humanize(item.origin)}</span>
      </div>
      {item.entity_refs.length > 0 && (
        <div className="entity-ref-row">
          <span>RELATED RECORDS</span>
          {item.entity_refs.map((id) => (
            <NavLink key={id} to={`/entities/${encodeURIComponent(id)}`}>
              {id} <ArrowRight size={12} />
            </NavLink>
          ))}
        </div>
      )}
      {item.source_refs.length > 0 && (
        <div className="quality-sources">
          <span>SOURCE REFERENCES</span>
          <div>
            {item.source_refs.map((reference) => (
              <code key={reference}>{reference}</code>
            ))}
          </div>
        </div>
      )}
      {item.route && item.route !== "/data-quality" && (
        <NavLink className="text-link quality-action" to={item.route}>
          View related information <ArrowRight size={14} />
        </NavLink>
      )}
    </article>
  );
}

function AboutPage() {
  const { data, error, loading, retry } = useResource(
    (signal) => api.about(signal),
    "about",
  );
  return (
    <>
      <PageHeading
        eyebrow="PROJECT CONTEXT"
        title="About INFONET"
        description="A read-only window into the CSE knowledge graph and the evidence behind it."
      />
      {loading && <LoadingState label="Loading project context" />}
      {error && <ErrorState error={error} retry={retry} />}
      {data && (
        <>
          <section className="panel about-intro">
            <span className="about-icon">
              <Network size={21} />
            </span>
            <div>
              <div className="section-eyebrow">{data.scope.institution}</div>
              <h2>{data.scope.department}</h2>
              <p>
                INFONET organizes available department information into a
                connected graph so it can be browsed and inspected alongside its
                source and review status.
              </p>
            </div>
          </section>
          <div className="about-grid">
            {Object.entries(data.scope).map(([key, value]) => (
              <div className="about-fact panel" key={key}>
                <span>{humanize(key)}</span>
                <strong>{value}</strong>
              </div>
            ))}
          </div>
          <section className="panel limitation-panel">
            <div className="panel-heading">
              <div>
                <div className="section-eyebrow">READ WITH CONTEXT</div>
                <h2>Known limitations</h2>
              </div>
              <span className="dataset-chip">
                {data.known_limitations.length} notes
              </span>
            </div>
            <div className="limitation-list">
              {data.known_limitations.map((item) => (
                <article key={item.id}>
                  <span className="limitation-id">{item.id}</span>
                  <div>
                    <strong>{item.title}</strong>
                    <p>{item.description}</p>
                  </div>
                </article>
              ))}
            </div>
          </section>
          <section className="panel run-panel">
            <div className="panel-heading">
              <div>
                <div className="section-eyebrow">PIPELINE METADATA</div>
                <h2>Source run</h2>
              </div>
              <Database size={17} />
            </div>
            {data.pipeline_run ? (
              <dl className="attribute-list compact-list">
                {Object.entries(data.pipeline_run)
                  .filter(([, value]) => value)
                  .map(([key, value]) => (
                    <div key={key}>
                      <dt>{humanize(key)}</dt>
                      <dd>{String(value)}</dd>
                    </div>
                  ))}
              </dl>
            ) : (
              <p className="muted-copy">
                No pipeline run metadata was returned by the API.
              </p>
            )}
          </section>
        </>
      )}
    </>
  );
}

function NotFound() {
  return (
    <div className="not-found">
      <CircleHelp size={26} />
      <div className="eyebrow">404 · NOT FOUND</div>
      <h1>That page isn’t here.</h1>
      <p>The requested INFONET page could not be found.</p>
      <NavLink className="button button-primary" to="/">
        Return to overview
      </NavLink>
    </div>
  );
}
function EntityIcon({ type }: { type: string }) {
  return type === "Person" ? (
    <Users size={18} />
  ) : type === "Program" ? (
    <GraduationCap size={18} />
  ) : type === "Laboratory" ? (
    <FlaskConical size={18} />
  ) : (
    <Network size={18} />
  );
}
function humanize(value: string): string {
  return value
    .replaceAll("_", " ")
    .replaceAll("-", " ")
    .toLowerCase()
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

class AppErrorBoundary extends Component<
  { children: ReactNode },
  { failed: boolean }
> {
  state = { failed: false };
  static getDerivedStateFromError(): { failed: boolean } {
    return { failed: true };
  }
  componentDidCatch(_error: Error, _info: ErrorInfo): void {
    /* Keep internal details out of the user interface. */
  }
  render(): ReactNode {
    if (this.state.failed)
      return (
        <main className="error-boundary">
          <div className="state-icon danger">
            <Activity size={20} />
          </div>
          <h1>This view could not be displayed.</h1>
          <p>Reload INFONET to try again. No project data was changed.</p>
          <button
            className="button button-primary"
            onClick={() => window.location.reload()}
          >
            <RefreshCw size={14} /> Reload page
          </button>
        </main>
      );
    return this.props.children;
  }
}

export default function App() {
  return (
    <BrowserRouter>
      <AppErrorBoundary>
        <AppShell />
      </AppErrorBoundary>
    </BrowserRouter>
  );
}
