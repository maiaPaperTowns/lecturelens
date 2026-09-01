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

describe("dashboard concept filters", () => {
  beforeEach(() => {
    getLecture.mockResolvedValue(lectureFixture);
    getConcepts.mockResolvedValue(conceptsFixture);
    getClusters.mockResolvedValue(clustersFixture);
  });

  function renderDashboard() {
    render(
      <MemoryRouter initialEntries={["/lectures/1"]}>
        <Routes>
          <Route path="/lectures/:lectureId" element={<LectureDashboardPage />} />
        </Routes>
      </MemoryRouter>,
    );
  }

  it("filters the table by difficulty", async () => {
    const user = userEvent.setup();
    renderDashboard();
    await screen.findByRole("table");

    await user.selectOptions(screen.getByLabelText("Filter by difficulty"), "hard");

    const table = screen.getByRole("table");
    expect(within(table).getByText("Loop Invariant")).toBeInTheDocument();
    expect(within(table).queryByText("Binary Search")).not.toBeInTheDocument();
    expect(screen.getByText(/Showing 1 of 3 concepts/)).toBeInTheDocument();
  });

  it("filters by concept type and can be reset", async () => {
    const user = userEvent.setup();
    renderDashboard();
    await screen.findByRole("table");

    await user.selectOptions(screen.getByLabelText("Filter by concept type"), "implementation_detail");
    expect(within(screen.getByRole("table")).getByText("Midpoint Overflow")).toBeInTheDocument();
    expect(within(screen.getByRole("table")).queryByText("Binary Search")).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /clear filters/i }));
    expect(screen.getByText(/Showing 3 of 3 concepts/)).toBeInTheDocument();
  });

  it("filters by cluster", async () => {
    const user = userEvent.setup();
    renderDashboard();
    await screen.findByRole("table");

    await user.selectOptions(screen.getByLabelText("Filter by cluster"), "101");
    const table = screen.getByRole("table");
    expect(within(table).getByText("Midpoint Overflow")).toBeInTheDocument();
    expect(within(table).queryByText("Loop Invariant")).not.toBeInTheDocument();
  });
});
