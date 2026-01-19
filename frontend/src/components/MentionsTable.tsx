"use client";

type Mention = {
  keyword: string;
  platform: string;
  content: string;
  url: string;
  sentiment?: string | null;
  emotion?: string | null;
  summary?: string | null;
};

type MentionsTableProps = {
  mentions: Mention[];
};

export function MentionsTable({ mentions }: MentionsTableProps) {
  return (
    <div className="rounded-lg border border-slate-800 bg-slate-950">
      <div className="border-b border-slate-800 px-4 py-3 text-sm text-slate-300">
        Latest Mentions
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-slate-800 text-slate-400">
            <tr>
              <th className="px-4 py-3">Platform</th>
              <th className="px-4 py-3">Summary</th>
              <th className="px-4 py-3">Emotion</th>
              <th className="px-4 py-3">Source</th>
            </tr>
          </thead>
          <tbody>
            {mentions.map((mention) => (
              <tr key={mention.url} className="border-b border-slate-900">
                <td className="px-4 py-3 capitalize text-slate-200">
                  {mention.platform}
                </td>
                <td className="px-4 py-3 text-slate-300">
                  {mention.summary ?? mention.content.slice(0, 120)}
                </td>
                <td className="px-4 py-3">
                  <span className="rounded-full bg-slate-800 px-2 py-1 text-xs text-slate-200">
                    {mention.emotion ?? "unknown"}
                  </span>
                </td>
                <td className="px-4 py-3">
                  <a
                    href={mention.url}
                    target="_blank"
                    rel="noreferrer"
                    className="text-emerald-400 hover:underline"
                  >
                    View
                  </a>
                </td>
              </tr>
            ))}
            {mentions.length === 0 && (
              <tr>
                <td
                  colSpan={4}
                  className="px-4 py-6 text-center text-slate-500"
                >
                  No mentions yet.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
