import Link from "next/link";

// Shared across the three library sub-pages (video, practice, summary) so
// "back" always lands on the listing page and the header stays consistent.
export function LibraryPageHeader({ title }: { title: string }) {
  return (
    <div className="flex items-center gap-3 mb-6">
      <Link
        href="/dashboard/library"
        aria-label="Back to Library"
        className="text-lg leading-none px-2.5 py-1.5 rounded border border-black/10 dark:border-white/10 hover:bg-black/5 dark:hover:bg-white/5"
      >
        ←
      </Link>
      <h1 className="text-2xl font-semibold">{title}</h1>
    </div>
  );
}
