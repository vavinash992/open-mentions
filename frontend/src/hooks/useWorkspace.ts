"use client";

import { useEffect, useState } from "react";

import { api } from "@/lib/api";

const STORAGE_KEY = "open_mentions_workspace_id";

export function useWorkspace() {
  const [workspaceId, setWorkspaceId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const initWorkspace = async () => {
      try {
        const existing = window.localStorage.getItem(STORAGE_KEY);
        if (existing) {
          setWorkspaceId(existing);
          return;
        }

        const response = await api.get("/api/v1/workspace/new");
        const id = response.data?.workspace_id as string;
        if (id) {
          window.localStorage.setItem(STORAGE_KEY, id);
          setWorkspaceId(id);
        }
      } catch (error) {
        // Fallback: keep null; UI can show error state
        console.error("Failed to initialize workspace", error);
      } finally {
        setLoading(false);
      }
    };

    initWorkspace();
  }, []);

  return { workspaceId, loading };
}
