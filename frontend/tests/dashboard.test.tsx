import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

const getLecture = vi.fn();
const getConcepts = vi.fn();
const getClusters = vi.fn();
vi.mock("../src/services/api", () => ({
  api: {
    getLecture: (...a: unknown[]) => getLecture(...a),
    getConcepts: (...a: unknown[]) => getConcepts(...a),
    getClusters: (...a: unknown[]) => getClusters(...a),
    analyzeLecture: vi.fn(),
  },
  ApiRequestError: class extends Error {},
}));

import { LectureDashboardPage } from "../src/pages/LectureDashboardPage";
import { clustersFixture, conceptsFixture, lectureFixture } from "./fixtures";

function renderDashboard() {
  return render(
    <MemoryRouter initialEntries={["/lectures/1"]}>
      <Routes>
        <Route path="/lectures/:lectureId" element={<LectureDashboardPage />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe("LectureDashboardPage", () => {
  beforeEach(() => {
    getLecture.mockResolvedValue(lectureFixture);
    getConcepts.mockResolvedValue(conceptsFixture);
    getClusters.mockResolvedValue(clustersFixture);
  });

  it("renders summary cards and the full concept table", async () => {
    renderDashboard();

    expect(await screen.findByRole("heading", { name: "Binary Search" })).toBeInTheDocument();
    expect(screen.getByText("Concepts")).toBeInTheDocument();
    expect(screen.getByText("Study clusters")).toBeInTheDocument();

    const table = await screen.findByRole("table");
    expect(within(table).getByText("Binary Search")).toBeInTheDocument();
    expect(within(table).getByText("Loop Invariant")).toBeInTheDocument();
    expect(within(table).getByText("Midpoint Overflow")).toBeInTheDocument();
    expect(screen.getByText(/Showing 3 of 3 concepts/)).toBeInTheDocument();
  });

  it("sorts by difficulty when the column header is clicked", async () => {
    const user = userEvent.setup();
    renderDashboard();
    await screen.findByText(/Showing 3 of 3 concepts/);

    await user.click(await screen.findByRole("button", { name: /^Difficulty/ }));

    const rows = screen.getAllByRole("row").slice(1); // drop header
    const firstConcept = within(rows[0]).getByRole("link").textContent;
    expect(firstConcept).toBe("Loop Invariant"); // hardest first (descending)
  });

  it("shows an analyze prompt when the lecture is not analyzed", async () => {
    getLecture.mockResolvedValue({ ...lectureFixture, status: "uploaded" });
    renderDashboard();
    expect(await screen.findByText(/hasn't been analyzed yet/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /run analysis/i })).toBeInTheDocument();
  });
});
