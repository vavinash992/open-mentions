"use client";

import { useEffect, useState } from "react";

import { api } from "@/lib/api";

const STORAGE_KEY = "open_mentions_workspace_id";

async function createNewWorkspace(): Promise<string | null> {
  const response = await api.get("/api/v1/workspace/new");
  const id = response.data?.workspace_id as string | undefined;
  if (id) {
    window.localStorage.setItem(STORAGE_KEY, id);
  }
  return id ?? null;
}

export function useWorkspace() {
  const [workspaceId, setWorkspaceId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const initWorkspace = async () => {
      try {
        const existing = window.localStorage.getItem(STORAGE_KEY);
        if (existing) {
          // Validate the stored workspace still exists in the backend
          try {
            await api.get(`/api/v1/analytics/summary?workspace_id=${existing}`);
            setWorkspaceId(existing);
            return;
          } catch (err: unknown) {
            const status = (err as { response?: { status?: number } })?.response?.status;
            if (status === 404) {
              // Workspace no longer exists — clear and create a new one
              console.warn("Stored workspace not found, creating a new one...");
              window.localStorage.removeItem(STORAGE_KEY);
            } else {
              // Non-404 error (network issue, etc.) — trust the stored ID
              setWorkspaceId(existing);
              return;
            }
          }
        }

        const id = await createNewWorkspace();
        if (id) setWorkspaceId(id);
      } catch (error) {
        console.error("Failed to initialize workspace", error);
      } finally {
        setLoading(false);
      }
    };

    initWorkspace();
  }, []);

  return { workspaceId, loading };
}
