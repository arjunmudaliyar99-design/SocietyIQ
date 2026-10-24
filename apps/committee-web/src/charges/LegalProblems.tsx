import { CircleAlert, TriangleAlert } from "lucide-react";

import { useTranslation } from "@societyiq/shared";

import type { LegalProblem } from "../api/charges";

/** Legal problems from the backend, in plain words with the rule they come from. */
export function LegalProblems({ problems }: { problems: LegalProblem[] }) {
  const { t } = useTranslation("committee");
  if (!problems.length) return null;
  return (
    <div role="alert">
      <ul className="flex flex-col gap-2">
      {problems.map((p, i) => (
        <li
          key={i}
          className={`flex gap-2 rounded-lg border-2 p-3 text-body ${p.level === "block" ? "border-red" : "border-terracotta"}`}
        >
          <span aria-hidden="true" className={p.level === "block" ? "text-red" : "text-terracotta"}>
            {p.level === "block" ? <CircleAlert size={22} /> : <TriangleAlert size={22} />}
          </span>
          <span>
            <span className="font-semibold">
              {p.level === "block" ? t("charges.blocked") : t("charges.warning")}{" "}
            </span>
            {t(`charges.problems.${p.key}`, {
              ...p.params,
              method: p.params.method ? t(`charges.method.${p.params.method}`) : undefined,
            })}
            {p.params.rule ? <span className="block text-small text-muted">{t("charges.ruleRef", { rule: p.params.rule })}</span> : null}
          </span>
        </li>
      ))}
      </ul>
    </div>
  );
}
