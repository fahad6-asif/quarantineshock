import { AlertTriangle, CircleHelp, CircleSlash, MapPinOff, type LucideIcon } from "lucide-react";

export type Status = "REVIEW" | "UNCLEAR" | "NOT_HOST" | "OUTSIDE";

// SPEC section 3: exact vocabulary. Never "cleared", "approved for shipment" or "safe".
export const STATUS: Record<Status, { label: string; short: string; color: string; icon: LucideIcon; meaning: string }> = {
  REVIEW: {
    label: "Needs review",
    short: "Review",
    color: "#F59E0B",
    icon: AlertTriangle,
    meaning: "Origin inside an active zone on the pickup date, commodity is a host, no exemption confirmed",
  },
  UNCLEAR: {
    label: "Unclear: human check",
    short: "Unclear",
    color: "#8B5CF6",
    icon: CircleHelp,
    meaning: "Missing coordinates, unsure commodity, or the sources don't settle this product form",
  },
  NOT_HOST: {
    label: "No flag: not a host",
    short: "Not host",
    color: "#64748B",
    icon: CircleSlash,
    meaning: "Inside the zone, but the commodity is not on the Mexfly host lists",
  },
  OUTSIDE: {
    label: "No flag: outside zone",
    short: "Outside",
    color: "#10B981",
    icon: MapPinOff,
    meaning: "Origin outside every active zone on the pickup date",
  },
};

export const STATUS_ORDER: Status[] = ["REVIEW", "UNCLEAR", "NOT_HOST", "OUTSIDE"];

export function isFlagged(s?: string | null) {
  return s === "REVIEW" || s === "UNCLEAR";
}
