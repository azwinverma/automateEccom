import type { PostStatus } from "@commerce-os/api-client";

export type PostAction = "submit" | "approve" | "reject" | "schedule" | "publishNow" | "unschedule" | "cancel";

export interface PostPerms {
  write: boolean;
  approve: boolean;
  publish: boolean;
}

/** Actions to offer for a post, mirroring the backend workflow (content/service.py). */
export function postActions(status: PostStatus, perms: PostPerms): PostAction[] {
  const out: PostAction[] = [];
  switch (status) {
    case "draft":
      if (perms.write) out.push("submit");
      break;
    case "pending_approval":
      if (perms.approve) out.push("approve", "reject");
      break;
    case "approved":
    case "failed":
      if (perms.publish) out.push("schedule", "publishNow");
      break;
    case "scheduled":
      if (perms.publish) out.push("unschedule");
      break;
    default:
      return [];
  }
  if (perms.write && ["draft", "pending_approval", "approved", "scheduled", "failed"].includes(status)) out.push("cancel");
  return out;
}

/** Only unscheduled posts can be edited; editing an approved one sends it back to draft. */
export function canEditPost(status: PostStatus): boolean {
  return status === "draft" || status === "pending_approval" || status === "approved";
}

export function editResetsApproval(status: PostStatus): boolean {
  return status === "approved" || status === "pending_approval";
}

/** Posts with no scheduled time that still need work (the "not scheduled yet" list). */
export function isUnscheduledWork(p: { status: PostStatus; scheduled_at: string | null }): boolean {
  return !p.scheduled_at && (p.status === "draft" || p.status === "pending_approval" || p.status === "approved" || p.status === "failed");
}
