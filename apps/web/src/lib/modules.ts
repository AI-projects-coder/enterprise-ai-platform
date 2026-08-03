export type ModuleDef = {
  route: string;
  label: string;
  icon: string;
  requiredPermission?: string;
};

export const MODULE_REGISTRY: ModuleDef[] = [
  { route: "/dashboard/chat", label: "Chat", icon: "💬" },
  { route: "/dashboard/knowledge", label: "Knowledge", icon: "📚" },
  { route: "/dashboard/analytics", label: "Analytics", icon: "📊" },
  { route: "/dashboard/team", label: "Team", icon: "👥" },
  { route: "/dashboard/video", label: "Video", icon: "🎬" },
  { route: "/dashboard/datasets", label: "Data Scientist", icon: "📈" },
  { route: "/dashboard/cloud-configs", label: "Cloud Architect", icon: "☁️" },
];
