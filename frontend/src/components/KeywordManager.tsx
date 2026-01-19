"use client";

import { useState } from "react";
import useSWR from "swr";

import { api } from "@/lib/api";

type Keyword = {
  id: number;
  keyword: string;
  is_active: boolean;
  created_at: string;
};

type KeywordListResponse = {
  workspace_id: string;
  total_keywords: number;
  active_keywords: number;
  max_allowed: number;
  keywords: Keyword[];
};

type KeywordManagerProps = {
  workspaceId: string;
};

export function KeywordManager({ workspaceId }: KeywordManagerProps) {
  const [newKeyword, setNewKeyword] = useState("");
  const { data, mutate, isLoading } = useSWR<KeywordListResponse>(
    workspaceId ? ["/api/v1/keywords", workspaceId] : null,
    ([url, ws]) =>
      api.get(url, { headers: { "X-Workspace-ID": ws } }).then((res) => res.data)
  );

  const addKeyword = async () => {
    const value = newKeyword.trim();
    if (!value) return;
    try {
      await api.post(
        "/api/v1/keywords",
        { keyword: value },
        { headers: { "X-Workspace-ID": workspaceId } }
      );
      setNewKeyword("");
      await mutate();
    } catch (error) {
      console.error("Failed to add keyword", error);
    }
  };

  const removeKeyword = async (id: number) => {
    try {
      await api.delete(`/api/v1/keywords/${id}`, {
        headers: { "X-Workspace-ID": workspaceId },
      });
      await mutate();
    } catch (error) {
      console.error("Failed to remove keyword", error);
    }
  };

  const activeCount = data?.active_keywords ?? 0;
  const maxAllowed = data?.max_allowed ?? 5;

  return (
    <div id="keywords" className="rounded-lg border border-slate-800 bg-slate-950 p-4">
      <div className="mb-3 flex items-center justify-between">
        <h3 className="text-sm font-medium text-slate-200">Keywords</h3>
        <span className="text-xs text-slate-500">
          {activeCount}/{maxAllowed}
        </span>
      </div>

      <div className="flex gap-2">
        <input
          value={newKeyword}
          onChange={(e) => setNewKeyword(e.target.value)}
          placeholder="Add keyword"
          className="w-full rounded-md border border-slate-800 bg-slate-900 px-3 py-2 text-sm text-slate-100 outline-none focus:border-emerald-400"
        />
        <button
          onClick={addKeyword}
          disabled={activeCount >= maxAllowed || isLoading}
          className="rounded-md bg-emerald-500 px-3 py-2 text-sm font-medium text-white disabled:cursor-not-allowed disabled:bg-slate-700"
        >
          Add
        </button>
      </div>

      <ul className="mt-4 space-y-2 text-sm">
        {data?.keywords?.map((kw) => (
          <li
            key={kw.id}
            className="flex items-center justify-between rounded-md border border-slate-800 bg-slate-900 px-3 py-2 text-slate-200"
          >
            <span>{kw.keyword}</span>
            <button
              onClick={() => removeKeyword(kw.id)}
              className="text-xs text-rose-400 hover:underline"
            >
              Remove
            </button>
          </li>
        ))}
        {!isLoading && (data?.keywords?.length ?? 0) === 0 && (
          <li className="text-slate-500">No keywords yet.</li>
        )}
      </ul>
    </div>
  );
}
