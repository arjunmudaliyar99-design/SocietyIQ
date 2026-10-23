import { MessageSquareWarning, Wallet } from "lucide-react";
import { useCallback, useState } from "react";

import {
  BigButton,
  Button,
  Card,
  ConfirmDialog,
  EmptyState,
  Field,
  MoneyText,
  StatCard,
  StatusPill,
  StepHeader,
  TextSizeSwitcher,
  Toast,
  formatDate,
  useSettings,
  useTranslation,
} from "@societyiq/shared";

/** All shared components in one page, for design review (docs/07 M1 task 2). Route: /preview */
export function Preview() {
  const { t } = useTranslation();
  const { language } = useSettings();
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [toastOpen, setToastOpen] = useState(false);
  const closeToast = useCallback(() => setToastOpen(false), []);

  return (
    <div className="flex flex-col gap-8">
      <h1 className="text-title font-bold">{t("preview.title")}</h1>

      <section className="flex flex-col gap-3">
        <BigButton icon={<Wallet size={24} />}>{t("preview.sampleYes")}</BigButton>
        <div className="flex flex-wrap gap-3">
          <Button>{t("confirm.yes")}</Button>
          <Button variant="secondary">{t("back")}</Button>
          <Button variant="danger">{t("close")}</Button>
        </div>
      </section>

      <section className="grid gap-4 sm:grid-cols-2">
        <StatCard
          label={t("preview.sampleStat")}
          value={<MoneyText paise={13100000} />}
          note={t("preview.sampleStatNote")}
          onClick={() => {}}
        />
        <Card>
          <p className="mb-3 text-body">
            <MoneyText paise={-50000} forResident /> · {formatDate("2026-09-25", language)}
          </p>
          <div className="flex flex-wrap gap-2">
            <StatusPill status="paid" />
            <StatusPill status="pending" />
            <StatusPill status="overdue" />
            <StatusPill status="open" />
            <StatusPill status="resolved" />
          </div>
        </Card>
      </section>

      <Card>
        <StepHeader current={2} total={3} title={t("preview.sampleField")} />
        <Field
          label={t("preview.sampleField")}
          help={t("preview.sampleFieldHelp")}
          error={t("preview.sampleFieldError")}
          inputMode="tel"
        />
      </Card>

      <EmptyState
        icon={<MessageSquareWarning size={40} />}
        message={t("preview.sampleEmpty")}
        actionLabel={t("preview.sampleEmptyAction")}
        onAction={() => {}}
      />

      <Card>
        <TextSizeSwitcher />
      </Card>

      <div className="flex flex-wrap gap-3">
        <Button variant="secondary" onClick={() => setConfirmOpen(true)}>
          {t("preview.showDialog")}
        </Button>
        <Button variant="secondary" onClick={() => setToastOpen(true)}>
          {t("preview.showToast")}
        </Button>
      </div>

      <ConfirmDialog
        open={confirmOpen}
        question={t("preview.sampleQuestion")}
        confirmLabel={t("preview.sampleYes")}
        onConfirm={() => {
          setConfirmOpen(false);
          setToastOpen(true);
        }}
        onCancel={() => setConfirmOpen(false)}
      />
      {toastOpen ? (
        <Toast
          message={t("preview.sampleToast")}
          actionLabel={t("preview.sampleUndo")}
          onAction={closeToast}
          onClose={closeToast}
        />
      ) : null}
    </div>
  );
}
