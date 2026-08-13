export type Priority = "low" | "medium" | "high" | "highest";
export type TicketStatus = "open" | "in_progress" | "resolved";

export type TicketAttachment = {
  id: string;
  storage_ref: string;
  content_type: string;
  view_url: string;
};

export type Ticket = {
  id: string;
  user_id: string;
  description: string;
  priority: Priority | null;
  status: TicketStatus;
  jira_issue_key: string | null;
  resolved_at: string | null;
  created_at: string;
};

export type TicketDetail = Ticket & {
  attachments: TicketAttachment[];
};
