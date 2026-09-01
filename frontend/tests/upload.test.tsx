import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

const navigate = vi.fn();
vi.mock("react-router-dom", async (importOriginal) => {
  const actual = await importOriginal<typeof import("react-router-dom")>();
  return { ...actual, useNavigate: () => navigate };
});

const uploadLecture = vi.fn();
const analyzeLecture = vi.fn();
vi.mock("../src/services/api", () => ({
  uploadLecture: (...args: unknown[]) => uploadLecture(...args),
  ApiRequestError: class extends Error {},
  api: { analyzeLecture: (...args: unknown[]) => analyzeLecture(...args) },
}));

import { UploadForm } from "../src/components/UploadForm";

function renderForm() {
  return render(
    <MemoryRouter>
      <UploadForm />
    </MemoryRouter>,
  );
}

describe("UploadForm", () => {
  beforeEach(() => {
    uploadLecture.mockResolvedValue({ lecture: { id: 7 }, message: "ok" });
    analyzeLecture.mockResolvedValue({ status: "analyzed" });
  });

  it("rejects unsupported file types", async () => {
    const user = userEvent.setup();
    renderForm();
    const input = screen.getByLabelText("Lecture files") as HTMLInputElement;
    await user.upload(
      input,
      new File(["x"], "notes.docx", { type: "application/octet-stream" }),
    );
    expect(await screen.findByText(/not a supported file type/i)).toBeInTheDocument();
    expect(screen.queryByTestId("file-list")).not.toBeInTheDocument();
  });

  it("requires course, title and a file before submitting", async () => {
    const user = userEvent.setup();
    renderForm();
    await user.click(screen.getByRole("button", { name: /upload & analyze/i }));
    expect(await screen.findByText(/are required/i)).toBeInTheDocument();
    expect(uploadLecture).not.toHaveBeenCalled();
  });

  it("uploads, triggers analysis and navigates to the dashboard", async () => {
    const user = userEvent.setup();
    renderForm();

    await user.type(screen.getByPlaceholderText(/CS 201/i), "CS 201");
    await user.type(screen.getByPlaceholderText(/Binary Search/i), "Merge Sort");
    await user.upload(
      screen.getByLabelText("Lecture files"),
      new File(["# notes"], "lecture.md", { type: "text/markdown" }),
    );
    expect(screen.getByTestId("file-list")).toHaveTextContent("lecture.md");

    await user.click(screen.getByRole("button", { name: /upload & analyze/i }));

    await waitFor(() => expect(uploadLecture).toHaveBeenCalledTimes(1));
    expect(uploadLecture.mock.calls[0][0]).toMatchObject({
      courseName: "CS 201",
      lectureTitle: "Merge Sort",
    });
    await waitFor(() => expect(analyzeLecture).toHaveBeenCalledWith(7));
    await waitFor(() => expect(navigate).toHaveBeenCalledWith("/lectures/7"));
  });
});
