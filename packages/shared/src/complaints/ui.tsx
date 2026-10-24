// Complaint pieces used by both apps (docs/02 §8): category icons, status pill, the raise form,
// photos and the update history.
import {
  ArrowUpDown,
  Camera,
  Car,
  CircleCheck,
  CircleDot,
  CircleHelp,
  Clock,
  Droplets,
  Home,
  Lock,
  Send,
  Shield,
  Sparkles,
  Trees,
  X,
  Zap,
} from "lucide-react";
import { useId, useRef, useState, type ReactNode } from "react";
import { useTranslation } from "react-i18next";

import { messageKeyOf } from "../auth/errors";
import { ErrorText } from "../auth/screens";
import { useSettings } from "../settings-context";
import { BigButton, Button } from "../ui/Button";
import { Card } from "../ui/Card";
import { SelectField } from "../ui/SelectField";
import { formatDate } from "../utils/date";
import {
  useComplaintPhoto,
  useRaiseComplaint,
  type Complaint,
  type ComplaintCategory,
  type ComplaintDetail,
  type ComplaintLocation,
  type ComplaintStatus,
} from "./api";

export const COMPLAINT_CATEGORIES: { value: ComplaintCategory; icon: ReactNode }[] = [
  { value: "water", icon: <Droplets size={28} /> },
  { value: "lift", icon: <ArrowUpDown size={28} /> },
  { value: "electricity", icon: <Zap size={28} /> },
  { value: "cleaning", icon: <Sparkles size={28} /> },
  { value: "security", icon: <Shield size={28} /> },
  { value: "parking", icon: <Car size={28} /> },
  { value: "other", icon: <CircleHelp size={28} /> },
];

export const COMPLAINT_STATUSES: ComplaintStatus[] = ["open", "in_progress", "resolved", "closed"];

// Word + icon + colour, never colour alone (docs/03 §3).
const STATUS_STYLE: Record<ComplaintStatus, { className: string; icon: ReactNode }> = {
  open: { className: "text-teal border-teal", icon: <CircleDot size={18} /> },
  in_progress: { className: "text-ink border-muted", icon: <Clock size={18} /> },
  resolved: { className: "text-green border-green", icon: <CircleCheck size={18} /> },
  closed: { className: "text-muted border-line", icon: <Lock size={18} /> },
};

export function ComplaintStatusPill({ status }: { status: ComplaintStatus }) {
  const { t } = useTranslation();
  const style = STATUS_STYLE[status];
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full border-2 bg-surface px-3 py-1 text-small font-semibold ${style.className}`}
    >
      <span aria-hidden="true">{style.icon}</span>
      {t(`complaints.status.${status}`)}
    </span>
  );
}

export function categoryIcon(category: ComplaintCategory): ReactNode {
  return COMPLAINT_CATEGORIES.find((c) => c.value === category)?.icon;
}

/** One row in a list: icon, category, flat or common area, date and status. */
export function ComplaintRow({ complaint, onOpen }: { complaint: Complaint; onOpen: () => void }) {
  const { t } = useTranslation();
  const { language } = useSettings();
  const where =
    complaint.location === "common_area" ? t("complaints.location.common_area") : (complaint.flat_label ?? "");
  return (
    <li>
      <button
        type="button"
        onClick={onOpen}
        className="flex w-full items-center gap-3 rounded-lg border-2 border-line bg-surface p-4 text-left focus-visible:outline-3 focus-visible:outline-offset-2 focus-visible:outline-ink"
      >
        <span aria-hidden="true" className="text-teal">
          {categoryIcon(complaint.category)}
        </span>
        <span className="flex flex-1 flex-col">
          <span className="text-body font-semibold">{t(`complaints.category.${complaint.category}`)}</span>
          <span className="text-small text-muted">
            {where ? `${where} · ` : ""}
            {formatDate(complaint.created_at.slice(0, 10), language)}
          </span>
        </span>
        <ComplaintStatusPill status={complaint.status} />
      </button>
    </li>
  );
}

// Phone photos are often 3-10 MB; a smaller JPEG uploads faster on a weak connection.
const MAX_SIDE = 1600;

async function shrinkPhoto(file: File): Promise<File> {
  if (typeof createImageBitmap !== "function" || !file.type.startsWith("image/")) return file;
  try {
    const bitmap = await createImageBitmap(file);
    const scale = Math.min(1, MAX_SIDE / Math.max(bitmap.width, bitmap.height));
    if (scale === 1 && file.size < 1_500_000) return file;
    const canvas = document.createElement("canvas");
    canvas.width = Math.round(bitmap.width * scale);
    canvas.height = Math.round(bitmap.height * scale);
    canvas.getContext("2d")?.drawImage(bitmap, 0, 0, canvas.width, canvas.height);
    const blob = await new Promise<Blob | null>((resolve) => canvas.toBlob(resolve, "image/jpeg", 0.85));
    return blob ? new File([blob], "photo.jpg", { type: "image/jpeg" }) : file;
  } catch {
    // Formats the browser cannot draw (e.g. HEIC on some phones) go as they are.
    return file;
  }
}

export interface ComplaintFormProps {
  /** Flats to choose from: the committee's whole list, or a resident's several flats. */
  flats?: { value: string; label: string }[];
  onDone: (complaint: ComplaintDetail) => void;
}

/** The "Report a problem" form: category, where, optional photo and text, one Send button. */
export function ComplaintForm({ flats, onDone }: ComplaintFormProps) {
  const { t } = useTranslation();
  const raise = useRaiseComplaint();
  const photoInput = useRef<HTMLInputElement>(null);
  const descriptionId = useId();
  const [category, setCategory] = useState<ComplaintCategory | null>(null);
  const [location, setLocation] = useState<ComplaintLocation>("my_flat");
  const [flatId, setFlatId] = useState("");
  const [photo, setPhoto] = useState<File | null>(null);
  const [description, setDescription] = useState("");
  const [tried, setTried] = useState(false);

  const needsFlat = Boolean(flats?.length) && location === "my_flat" && !flatId;
  const missing = !category || needsFlat;

  async function send() {
    setTried(true);
    if (missing || !category) return;
    const small = photo ? await shrinkPhoto(photo) : null;
    raise.mutate(
      {
        complaint: {
          category,
          location,
          flat_id: flats?.length ? flatId || null : null,
          description: description.trim() || null,
        },
        photo: small,
      },
      { onSuccess: onDone },
    );
  }

  return (
    <div className="flex flex-col gap-6">
      <fieldset>
        <legend className="mb-3 text-section font-bold">{t("complaints.form.what")}</legend>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
          {COMPLAINT_CATEGORIES.map((c) => (
            <button
              key={c.value}
              type="button"
              aria-pressed={category === c.value}
              onClick={() => setCategory(c.value)}
              className={`flex min-h-[88px] flex-col items-center justify-center gap-2 rounded-xl border-2 p-3 text-body font-semibold focus-visible:outline-3 focus-visible:outline-offset-2 focus-visible:outline-ink ${
                category === c.value ? "border-teal bg-teal text-white" : "border-line bg-surface text-ink"
              }`}
            >
              <span aria-hidden="true">{c.icon}</span>
              {t(`complaints.category.${c.value}`)}
            </button>
          ))}
        </div>
        {tried && !category ? <ErrorText>{t("complaints.form.pickCategory")}</ErrorText> : null}
      </fieldset>

      <fieldset>
        <legend className="mb-3 text-section font-bold">{t("complaints.form.where")}</legend>
        <div className="grid grid-cols-2 gap-3">
          {(
            [
              ["my_flat", <Home key="i" size={24} />],
              ["common_area", <Trees key="i" size={24} />],
            ] as const
          ).map(([value, icon]) => (
            <button
              key={value}
              type="button"
              aria-pressed={location === value}
              onClick={() => setLocation(value)}
              className={`flex min-h-[64px] items-center justify-center gap-2 rounded-xl border-2 p-3 text-body font-semibold focus-visible:outline-3 focus-visible:outline-offset-2 focus-visible:outline-ink ${
                location === value ? "border-teal bg-teal text-white" : "border-line bg-surface text-ink"
              }`}
            >
              <span aria-hidden="true">{icon}</span>
              {t(`complaints.location.${value}`)}
            </button>
          ))}
        </div>
      </fieldset>

      {flats?.length ? (
        <div>
          <SelectField
            label={t("complaints.form.flat")}
            value={flatId}
            onChange={(e) => setFlatId(e.target.value)}
            options={[{ value: "", label: t("complaints.form.chooseFlat") }, ...flats]}
          />
          {tried && needsFlat ? <ErrorText>{t("complaints.form.pickFlat")}</ErrorText> : null}
        </div>
      ) : null}

      <div className="flex flex-col gap-2">
        <p className="text-section font-bold">{t("complaints.form.photo")}</p>
        <input
          ref={photoInput}
          type="file"
          accept="image/jpeg,image/png,image/webp"
          className="sr-only"
          tabIndex={-1}
          aria-label={t("complaints.form.addPhoto")}
          onChange={(e) => setPhoto(e.target.files?.[0] ?? null)}
        />
        {photo ? (
          <div className="flex items-center gap-3">
            <span className="text-body">{t("complaints.form.photoAdded")}</span>
            <Button variant="secondary" icon={<X size={22} />} onClick={() => setPhoto(null)}>
              {t("complaints.form.removePhoto")}
            </Button>
          </div>
        ) : (
          <div>
            <Button variant="secondary" icon={<Camera size={22} />} onClick={() => photoInput.current?.click()}>
              {t("complaints.form.addPhoto")}
            </Button>
          </div>
        )}
      </div>

      <div className="flex flex-col gap-1">
        <label htmlFor={descriptionId} className="text-section font-bold">
          {t("complaints.form.describe")}
        </label>
        <textarea
          id={descriptionId}
          rows={3}
          maxLength={2000}
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          className="rounded-lg border-2 border-line bg-surface p-3 text-body focus-visible:outline-3 focus-visible:outline-offset-2 focus-visible:outline-ink"
        />
      </div>

      <BigButton icon={<Send size={24} />} onClick={() => void send()} disabled={raise.isPending}>
        {raise.isPending ? t("complaints.form.sending") : t("complaints.form.send")}
      </BigButton>
      {raise.isError ? <ErrorText>{t(messageKeyOf(raise.error))}</ErrorText> : null}
    </div>
  );
}

function Photo({ complaintId, photoId, index }: { complaintId: string; photoId: string; index: number }) {
  const { t } = useTranslation();
  const url = useComplaintPhoto(complaintId, photoId);
  if (!url) return <div className="h-32 w-32 rounded-lg border-2 border-line bg-surface" />;
  return (
    <a href={url} target="_blank" rel="noopener noreferrer" className="block">
      <img
        src={url}
        alt={t("complaints.photoAlt", { n: index + 1 })}
        className="h-32 w-32 rounded-lg border-2 border-line object-cover"
      />
    </a>
  );
}

export function ComplaintPhotos({ complaint }: { complaint: ComplaintDetail }) {
  if (!complaint.photo_ids?.length) return null;
  return (
    <div className="flex flex-wrap gap-3">
      {complaint.photo_ids.map((id, i) => (
        <Photo key={id} complaintId={complaint.id} photoId={id} index={i} />
      ))}
    </div>
  );
}

/** What happened so far, oldest first. Resident feedback is stored as an i18n key. */
export function ComplaintHistory({ complaint }: { complaint: ComplaintDetail }) {
  const { t } = useTranslation();
  const { language } = useSettings();
  const updates = complaint.updates ?? [];
  return (
    <Card>
      <h2 className="mb-3 text-section font-bold">{t("complaints.history")}</h2>
      <ol className="flex flex-col gap-3">
        <li className="border-l-4 border-teal pl-3">
          <p className="text-small text-muted">{formatDate(complaint.created_at.slice(0, 10), language)}</p>
          <p className="text-body">
            {complaint.raised_on_behalf ? t("complaints.raisedOnBehalf") : t("complaints.raised")}
          </p>
        </li>
        {updates.map((u) => (
          <li key={u.id} className={`border-l-4 pl-3 ${u.visible_to_resident ? "border-teal" : "border-muted"}`}>
            <p className="text-small text-muted">
              {formatDate(u.created_at.slice(0, 10), language)}
              {u.new_status ? ` · ${t(`complaints.status.${u.new_status}`)}` : ""}
              {u.visible_to_resident ? "" : ` · ${t("complaints.committeeOnly")}`}
            </p>
            <p className="whitespace-pre-line text-body">
              {u.message.startsWith("complaints.feedback.") ? t(u.message) : u.message}
            </p>
          </li>
        ))}
      </ol>
    </Card>
  );
}
