import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

const submitFeedback = vi.fn();
vi.mock("../src/services/api", () => ({
  api: { submitFeedback: (...a: unknown[]) => submitFeedback(...a) },
  ApiRequestError: class extends Error {},
}));

import { FeedbackControls } from "../src/components/FeedbackControls";
import { conceptDetailFixture } from "./fixtures";

describe("FeedbackControls", () => {
  it("submits a classification correction and shows confirmation", async () => {
    const user = userEvent.setup();
    submitFeedback.mockResolvedValue({});
    const onSubmitted = vi.fn();

    render(<FeedbackControls concept={conceptDetailFixture} onSubmitted={onSubmitted} />);

    await user.click(screen.getByRole("button", { name: /^incorrect$/i }));
    await user.selectOptions(screen.getByLabelText("Corrected concept type"), "example");
    await user.click(screen.getByRole("button", { name: /submit feedback/i }));

    await waitFor(() =>
      expect(submitFeedback).toHaveBeenCalledWith(
        conceptDetailFixture.id,
        expect.objectContaining({
          classification_is_correct: false,
          corrected_label: "example",
        }),
      ),
    );
    expect(await screen.findByText(/your feedback was recorded/i)).toBeInTheDocument();
    expect(onSubmitted).toHaveBeenCalled();
  });

  it("keeps the submit button disabled until the user gives some feedback", () => {
    render(<FeedbackControls concept={conceptDetailFixture} />);
    expect(screen.getByRole("button", { name: /submit feedback/i })).toBeDisabled();
  });

  it("submits a difficulty direction without a label change", async () => {
    const user = userEvent.setup();
    submitFeedback.mockResolvedValue({});
    render(<FeedbackControls concept={conceptDetailFixture} />);

    await user.click(screen.getByRole("button", { name: /too hard/i }));
    await user.click(screen.getByRole("button", { name: /submit feedback/i }));

    await waitFor(() =>
      expect(submitFeedback).toHaveBeenCalledWith(
        conceptDetailFixture.id,
        expect.objectContaining({ difficulty_direction: "too_hard" }),
      ),
    );
  });
});
