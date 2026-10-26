import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import App from "./App";
import type { EntitySummary, SummaryResponse } from "./api/types";

const summary: SummaryResponse = {
  department: {
    id: "DEPT-1",
    name: "Computer Science & Engineering",
    description: "Department description from the live API.",
    source_url: "https://sit.ac.in/",
  },
  department_count: 1,
  counts: {
    people: 59,
    faculty: 47,
    support_staff: 12,
    laboratories: 14,
    programs: 7,
    relationships: 81,
  },
  data_status: {
    relationships_total: 81,
    relationships_inferred: 80,
    relationships_user_confirmed: 1,
    unverified_claims: 1,
    conflicts: 1,
    open_data_quality_items: 5,
  },
};
const person: EntitySummary = {
  id: "PERSON-1",
  type: "Person",
  name: "Dr. R Sumathi",
  attributes: { role_title: "Professor & HOD", person_category: "Professor" },
  missing_fields: [],
  status: {
    raw: { extraction_status: "derived_from_saved_snapshot_needs_review" },
    display_codes: ["source_stated_needs_review"],
  },
  provenance: {
    source_url: "https://sit.ac.in/example",
    source_section: "faculty",
  },
};
const program: EntitySummary = {
  id: "PROGRAM-1",
  type: "Program",
  name: "B.E. Computer Science and Engineering (Evening Program for Working Professionals)",
  attributes: {
    level: "UG",
    duration: "3 years",
    conflict_group: "PROG-CONFLICT-001",
  },
  missing_fields: [],
  status: {
    raw: { extraction_status: "derived_from_saved_snapshot_needs_review" },
    display_codes: ["source_stated_needs_review"],
  },
  provenance: {},
  conflict: { status_code: "unresolved_conflict" },
};

const mocks = vi.hoisted(() => ({
  api: {
    health: vi.fn(),
    summary: vi.fn(),
    dataQuality: vi.fn(),
    people: vi.fn(),
    laboratories: vi.fn(),
    programs: vi.fn(),
    about: vi.fn(),
    graph: vi.fn(),
    entity: vi.fn(),
  },
}));
vi.mock("./api/client", () => ({
  api: mocks.api,
  getErrorMessage: (error: unknown) =>
    error instanceof Error ? error.message : "Request failed",
}));

describe("INFONET application", () => {
  beforeEach(() => {
    window.history.replaceState({}, "", "/");
    mocks.api.health.mockResolvedValue({
      api: "up",
      database: "up",
      data_loaded: true,
    });
    mocks.api.summary.mockResolvedValue(summary);
    mocks.api.dataQuality.mockResolvedValue({ items: [], total: 0 });
    mocks.api.people.mockResolvedValue({
      items: [person],
      total: 1,
      limit: 12,
      offset: 0,
      facets: {},
    });
    mocks.api.laboratories.mockResolvedValue({
      items: [],
      total: 0,
      limit: 12,
      offset: 0,
      facets: {},
    });
    mocks.api.programs.mockResolvedValue({
      items: [program],
      total: 1,
      limit: 12,
      offset: 0,
      facets: {},
    });
    mocks.api.about.mockResolvedValue({
      scope: {
        institution: "SIT",
        department: "CSE",
        scope: "CSE-only MVP",
        language: "English only",
        access_mode: "Read-only",
        data_source: "Normalized dataset",
      },
      pipeline_run: null,
      known_limitations: [],
    });
    mocks.api.graph.mockResolvedValue({
      nodes: [],
      edges: [],
      meta: { node_count: 0, edge_count: 0, relationship_types: [] },
    });
  });
  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  it("renders live dashboard counts and describes review status", async () => {
    render(<App />);
    expect(
      await screen.findByRole("heading", {
        name: "Computer Science & Engineering",
      }),
    ).toBeInTheDocument();
    expect(screen.getByText("47")).toBeInTheDocument();
    expect(
      screen.getByText("80 inferred links need review"),
    ).toBeInTheDocument();
    expect(mocks.api.summary).toHaveBeenCalled();
  });

  it("keeps conflicting program records visibly unresolved", async () => {
    render(<App />);
    fireEvent.click(screen.getByRole("link", { name: "Programs" }));
    expect(
      await screen.findByText(/Conflicting records are preserved/),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/Conflict · both records retained/),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/Evening Program for Working Professionals/),
    ).toBeInTheDocument();
  });

  it("renders people from the API and submits debounced search", async () => {
    render(<App />);
    fireEvent.click(screen.getByRole("link", { name: "People" }));
    expect(await screen.findByText("Dr. R Sumathi")).toBeInTheDocument();
    fireEvent.change(screen.getByRole("textbox", { name: "Search people" }), {
      target: { value: "Sumathi" },
    });
    await waitFor(
      () =>
        expect(mocks.api.people).toHaveBeenCalledWith(
          expect.objectContaining({ q: "Sumathi" }),
          expect.any(AbortSignal),
        ),
      { timeout: 2000 },
    );
  });
});
