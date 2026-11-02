import { screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { en } from "@/i18n/messages/en";
import { renderWithI18n } from "@/test/render";
import { AutopilotStatusStrip } from "./AutopilotStatusStrip";

describe("AutopilotStatusStrip", () => {
  it("shows honest empty copy and the locked-modes note in Phase 0", () => {
    renderWithI18n(<AutopilotStatusStrip mode="assisted" automatedCount={0} needsAttentionCount={0} lockedUntilPhase={3} />);
    expect(screen.getByRole("img", { name: "Current mode: Assisted" })).toBeInTheDocument();
    expect(screen.getByTestId("automated-count")).toHaveTextContent("0");
    expect(screen.getByText(en.autopilot.emptyCounts)).toBeInTheDocument();
    expect(screen.getByText("Smart and Autopilot modes unlock when automations arrive.")).toBeInTheDocument();
  });

  it("shows a dash, not a fake zero, when counts are unmeasured", () => {
    renderWithI18n(<AutopilotStatusStrip mode="smart" automatedCount={null} needsAttentionCount={null} />);
    expect(screen.getByTestId("attention-count")).toHaveTextContent("—");
  });

  it("describes the mode when there is activity", () => {
    renderWithI18n(<AutopilotStatusStrip mode="smart" automatedCount={1280} needsAttentionCount={4} />);
    expect(screen.getByTestId("automated-count")).toHaveTextContent("1,280");
    expect(screen.getByText(en.autopilot.smartHelp)).toBeInTheDocument();
  });
});
