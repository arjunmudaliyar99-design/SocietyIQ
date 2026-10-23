import { act, fireEvent, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { useSettings } from "../settings-context";
import { renderWithSettings, seriousAxeViolations } from "../test-utils";
import { BigButton, Button } from "./Button";
import { Card, StatCard } from "./Card";
import { ConfirmDialog } from "./Dialog";
import { Field } from "./Field";
import { MoneyText } from "./MoneyText";
import { HelpButton, LanguageSwitcher, TextSizeSwitcher } from "./Settings";
import { EmptyState, StepHeader } from "./Small";
import { StatusPill } from "./StatusPill";
import { MIN_TOAST_MS, Toast } from "./Toast";

describe("Button and BigButton", () => {
  it("show the label and call onClick", () => {
    const onClick = vi.fn();
    renderWithSettings(
      <Button onClick={onClick} icon={<svg />}>
        Save
      </Button>,
    );
    fireEvent.click(screen.getByRole("button", { name: "Save" }));
    expect(onClick).toHaveBeenCalledOnce();
  });

  it("use the minimum heights from docs/03 §5", () => {
    renderWithSettings(
      <>
        <Button>Small</Button>
        <BigButton>Big</BigButton>
      </>,
    );
    expect(screen.getByRole("button", { name: "Small" }).className).toContain("min-h-[48px]");
    expect(screen.getByRole("button", { name: "Big" }).className).toContain("min-h-[56px]");
  });
});

describe("MoneyText", () => {
  it("formats paise in Indian grouping", () => {
    renderWithSettings(<MoneyText paise={13100000} />);
    expect(screen.getByText("₹1,31,000")).toBeTruthy();
  });

  it("shows a resident's negative balance as an advance", () => {
    renderWithSettings(<MoneyText paise={-50000} forResident />);
    expect(screen.getByText("₹500 advance")).toBeTruthy();
  });

  it("is masked from analytics", () => {
    renderWithSettings(<MoneyText paise={100} />);
    expect(screen.getByText("₹1").className).toContain("ph-no-capture");
  });
});

describe("StatusPill", () => {
  it.each([
    ["paid", "Paid"],
    ["pending", "Pending"],
    ["overdue", "Overdue"],
    ["open", "Open"],
    ["resolved", "Resolved"],
  ] as const)("%s shows the word %s", (status, word) => {
    renderWithSettings(<StatusPill status={status} />);
    expect(screen.getByText(word)).toBeTruthy();
  });
});

describe("Field", () => {
  it("links label, help and error to the input", () => {
    renderWithSettings(
      <Field label="Phone number" help="10 digits" error="Phone number needs 10 digits" />,
    );
    const input = screen.getByLabelText("Phone number");
    expect(input.getAttribute("aria-invalid")).toBe("true");
    expect((input.getAttribute("aria-describedby") ?? "").split(" ")).toHaveLength(2);
  });
});

describe("ConfirmDialog", () => {
  it("puts the safe choice first and focuses it", () => {
    const onConfirm = vi.fn();
    renderWithSettings(
      <ConfirmDialog
        open
        question="Record ₹4,200 cash from Flat B-207?"
        confirmLabel="Yes, record"
        onConfirm={onConfirm}
        onCancel={() => {}}
      />,
    );
    const buttons = screen.getAllByRole("button");
    expect(buttons[0]?.textContent).toBe("No, go back");
    expect(document.activeElement).toBe(buttons[0]);
    fireEvent.click(screen.getByRole("button", { name: "Yes, record" }));
    expect(onConfirm).toHaveBeenCalledOnce();
  });

  it("Escape cancels", () => {
    const onCancel = vi.fn();
    renderWithSettings(
      <ConfirmDialog open question="Q?" confirmLabel="Yes" onConfirm={() => {}} onCancel={onCancel} />,
    );
    fireEvent.keyDown(document, { key: "Escape" });
    expect(onCancel).toHaveBeenCalledOnce();
  });
});

describe("Toast", () => {
  it("never closes before 6 seconds, even if asked to", () => {
    vi.useFakeTimers();
    const onClose = vi.fn();
    renderWithSettings(<Toast message="Recorded." onClose={onClose} durationMs={1000} />);
    act(() => {
      vi.advanceTimersByTime(MIN_TOAST_MS - 1);
    });
    expect(onClose).not.toHaveBeenCalled();
    act(() => {
      vi.advanceTimersByTime(1);
    });
    expect(onClose).toHaveBeenCalledOnce();
    vi.useRealTimers();
  });
});

describe("EmptyState and StepHeader", () => {
  it("show the sentence, one action, and the step", () => {
    const onAction = vi.fn();
    renderWithSettings(
      <>
        <EmptyState message="No complaints yet." actionLabel="Report a problem" onAction={onAction} />
        <StepHeader current={2} total={3} title="Flats" />
      </>,
    );
    fireEvent.click(screen.getByRole("button", { name: "Report a problem" }));
    expect(onAction).toHaveBeenCalledOnce();
    expect(screen.getByText("Step 2 of 3")).toBeTruthy();
  });
});

describe("StatCard", () => {
  it("is one button when tappable", () => {
    const onClick = vi.fn();
    renderWithSettings(<StatCard label="Open complaints" value="4" onClick={onClick} />);
    fireEvent.click(screen.getByRole("button", { name: /Open complaints/ }));
    expect(onClick).toHaveBeenCalledOnce();
  });
});

function LanguageProbe() {
  const { language } = useSettings();
  return <p data-testid="lang">{language}</p>;
}

describe("LanguageSwitcher", () => {
  it("lists languages in their own scripts and switches visible text", () => {
    renderWithSettings(
      <>
        <LanguageSwitcher />
        <StatusPill status="paid" />
        <LanguageProbe />
      </>,
    );
    for (const name of ["English", "मराठी", "हिंदी", "ગુજરાતી", "தமிழ்"]) {
      expect(screen.getByRole("option", { name })).toBeTruthy();
    }
    fireEvent.change(screen.getByLabelText("Language"), { target: { value: "mr" } });
    expect(screen.getByTestId("lang").textContent).toBe("mr");
    expect(screen.getByText("भरले")).toBeTruthy();
    expect(document.documentElement.lang).toBe("mr");
  });
});

describe("TextSizeSwitcher", () => {
  it("sets the root size variable and remembers it", () => {
    renderWithSettings(<TextSizeSwitcher />);
    fireEvent.click(screen.getByRole("button", { name: "Extra large" }));
    expect(document.documentElement.style.getPropertyValue("--siq-root-size")).toBe("24px");
    expect(window.localStorage.getItem("societyiq.settings")).toContain("xlarge");
  });
});

describe("HelpButton", () => {
  it("shows support contact from props and a note when the society has none", () => {
    renderWithSettings(<HelpButton support={{ email: "support@example.com" }} />);
    fireEvent.click(screen.getByRole("button", { name: "Help" }));
    expect(screen.getByRole("dialog", { name: "Help" })).toBeTruthy();
    expect(screen.getByText("support@example.com")).toBeTruthy();
    expect(screen.getByText("Your society has not added a contact yet.")).toBeTruthy();
  });
});

describe("accessibility", () => {
  it("components have no serious axe violations", async () => {
    const { container } = renderWithSettings(
      <main>
        <h1>Preview</h1>
        <LanguageSwitcher />
        <TextSizeSwitcher />
        <Card>
          <StatusPill status="overdue" />
          <MoneyText paise={420000} />
        </Card>
        <StatCard label="Collected" value="₹1,31,000" note="From 42 payments" onClick={() => {}} />
        <Field label="Phone number" error="Phone number needs 10 digits" />
        <EmptyState message="No complaints yet." actionLabel="Report a problem" onAction={() => {}} />
        <HelpButton support={{ email: "support@example.com" }} />
      </main>,
    );
    expect(await seriousAxeViolations(container)).toEqual([]);
  });
});
